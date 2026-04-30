"""Two-stage anomaly detection.

Stage 1 (AI-11): rule-based threshold check, deterministic, fast.
Stage 2 (AI-12): LLM-based root-cause analysis grounded in manual chunks.

The two stages are kept in one module because Stage 2's prompt always
includes Stage 1's output, and they share the SensorLog input shape.
"""

from __future__ import annotations

import json
import logging
import re
import time
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

from langchain_core.embeddings import Embeddings
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import HumanMessage, SystemMessage

from app.config import Settings, get_settings
from app.core import prompt_loader
from app.core.embeddings import get_embeddings
from app.core.llm import get_llm
from app.core.vectorstore import SearchResult, VectorStore
from app.schemas.sensor_log import (
    AnomalyResponse,
    ManualReference,
    RuleResult,
    SensorLog,
    Severity,
    TriggeredRule,
)

logger = logging.getLogger(__name__)

RULES_PATH = Path(__file__).resolve().parents[2] / "data" / "anomaly_rules.json"

# Same dual-injection pattern as RagPipeline (see project_qwen3_no_think
# memory): system role + user content prefix.
_NO_THINK = SystemMessage(content="/no_think")

_SEVERITY_ORDER: dict[Severity, int] = {
    "low": 0,
    "medium": 1,
    "high": 2,
    "critical": 3,
}

_OPERATORS = {
    ">":  lambda a, b: a >  b,
    ">=": lambda a, b: a >= b,
    "<":  lambda a, b: a <  b,
    "<=": lambda a, b: a <= b,
    "==": lambda a, b: a == b,
}

# Used by the LLM parser. Kept simple — `re.findall` is enough for the
# 4-section format defined in `prompts/anomaly_analysis.txt`.
_ERROR_CODE_RE = re.compile(r"\bE-\d{3}\b")
_MANUAL_REF_RE = re.compile(
    r"\(\s*출처\s*[::]\s*(?P<file>[^,]+?\.pdf)\s*,\s*p\.?\s*(?P<page>\d+)\s*\)",
)


# ============================================================
# Stage 1 — rule engine
# ============================================================


@lru_cache(maxsize=1)
def _load_rules() -> list[dict]:
    if not RULES_PATH.exists():
        raise FileNotFoundError(f"anomaly rules not found: {RULES_PATH}")
    payload = json.loads(RULES_PATH.read_text(encoding="utf-8"))
    rules = payload.get("rules", [])
    for r in rules:
        if r["operator"] not in _OPERATORS:
            raise ValueError(f"unknown operator in rule {r['rule_id']!r}: {r['operator']}")
    return rules


def evaluate_rules(log: SensorLog, *, rules: list[dict] | None = None) -> RuleResult:
    """Run all rules whose `equipment_id` matches `log`."""
    rules = rules if rules is not None else _load_rules()
    triggered: list[TriggeredRule] = []
    for r in rules:
        if r["equipment_id"] != log.equipment_id:
            continue
        observed = log.readings.get(r["metric"])
        if observed is None:
            continue
        op = _OPERATORS[r["operator"]]
        if op(observed, r["threshold"]):
            triggered.append(
                TriggeredRule(
                    rule_id=r["rule_id"],
                    metric=r["metric"],
                    operator=r["operator"],
                    threshold=float(r["threshold"]),
                    observed=float(observed),
                    severity=r["severity"],
                    description=r["description"],
                )
            )

    if not triggered:
        return RuleResult(is_anomaly=False)

    max_sev = max(triggered, key=lambda t: _SEVERITY_ORDER[t.severity]).severity
    return RuleResult(is_anomaly=True, severity=max_sev, triggered_rules=triggered)


# ============================================================
# Stage 2 — LLM analysis
# ============================================================


@dataclass
class AnomalyPipeline:
    settings: Settings
    embedder: Embeddings
    llm: BaseChatModel
    store: VectorStore

    @classmethod
    def build(cls, settings: Settings | None = None) -> "AnomalyPipeline":
        settings = settings or get_settings()
        return cls(
            settings=settings,
            embedder=get_embeddings(settings),
            llm=get_llm(settings),
            store=VectorStore(settings),
        )

    def analyze(self, log: SensorLog) -> AnomalyResponse:
        t0 = time.perf_counter()

        rule_result = evaluate_rules(log)

        # If the deterministic rule engine sees nothing, skip the LLM:
        # a small local model tends to "find" issues out of an empty
        # context, and burning ~8s + a hallucinated error code helps
        # nobody. Status mirrors the rule verdict.
        if not rule_result.is_anomaly:
            latency_ms = int((time.perf_counter() - t0) * 1000)
            return AnomalyResponse(
                rule_result=rule_result,
                status="정상",
                probable_cause="",
                recommended_action="",
                related_error_codes=[],
                manual_refs=[],
                raw_answer="",
                latency_ms=latency_ms,
            )

        # 1) build a retrieval query from the rule output and pull RAG
        # context for the LLM.
        query = self._compose_retrieval_query(log, rule_result)
        qvec = self.embedder.embed_query(query)
        chunks = self.store.similarity_search(
            qvec,
            k=self.settings.retrieval_top_k,
            equipment_id=log.equipment_id,
        )
        kept = [c for c in chunks if c.similarity >= self.settings.similarity_threshold]
        context = self._format_context(kept) if kept else "(관련 매뉴얼 컨텍스트 없음)"

        # 2) prompt + LLM
        prompt = prompt_loader.render(
            "anomaly_analysis",
            rule_result=rule_result.model_dump_json(indent=2),
            sensor_log=log.model_dump_json(indent=2),
            context=context,
        )
        answer = self.llm.invoke(
            [_NO_THINK, HumanMessage(content=f"/no_think\n\n{prompt}")]
        ).content

        # 3) parse the structured sections
        status = self._extract_status(answer, rule_result)
        probable_cause = self._extract_section(answer, "추정 원인")
        recommended_action = self._extract_section(answer, "권장 조치")
        codes = sorted(set(_ERROR_CODE_RE.findall(answer)))
        refs = [
            ManualReference(manual=m.group("file").strip(), page=int(m.group("page")))
            for m in _MANUAL_REF_RE.finditer(answer)
        ]

        latency_ms = int((time.perf_counter() - t0) * 1000)
        return AnomalyResponse(
            rule_result=rule_result,
            status=status,
            probable_cause=probable_cause,
            recommended_action=recommended_action,
            related_error_codes=codes,
            manual_refs=refs,
            raw_answer=answer,
            latency_ms=latency_ms,
        )

    # ---- helpers ----

    @staticmethod
    def _compose_retrieval_query(log: SensorLog, rr: RuleResult) -> str:
        if rr.triggered_rules:
            return " ".join(t.description for t in rr.triggered_rules)
        # No rule fired — search by raw readings as a weak fallback.
        readings_str = ", ".join(f"{k}={v}" for k, v in log.readings.items())
        return f"{log.equipment_id} 정상 운전 범위 점검 ({readings_str})"

    @staticmethod
    def _format_context(chunks: list[SearchResult]) -> str:
        # Same per-chunk truncation as the RAG pipeline — local 9B/3B
        # models slow down quickly with long contexts.
        max_chars = 600
        blocks = [
            f"[매뉴얼: {c.manual_id}.pdf, 페이지: {c.page}]\n{c.chunk_text[:max_chars]}"
            for c in chunks
        ]
        return "\n\n---\n\n".join(blocks)

    @staticmethod
    def _extract_status(answer: str, rr: RuleResult) -> str:
        # The prompt asks for "1) 이상 판정: (정상 | 주의 | 이상)".
        m = re.search(r"이상\s*판정\s*[::]\s*(정상|주의|이상)", answer)
        if m:
            return m.group(1)
        # Fall back to the rule-engine verdict if the LLM didn't comply.
        if rr.is_anomaly:
            return "이상" if rr.severity in {"high", "critical"} else "주의"
        return "정상"

    @staticmethod
    def _extract_section(answer: str, header: str) -> str:
        # Sections are introduced by a numbered header line like
        # "2) 추정 원인:" — capture until the next "N)" header or EOF.
        pattern = rf"\d\)\s*{re.escape(header)}\s*[::]?\s*(.+?)(?=\n\s*\d\)|\Z)"
        m = re.search(pattern, answer, flags=re.DOTALL)
        return m.group(1).strip() if m else ""
