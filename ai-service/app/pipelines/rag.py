"""RAG orchestration: retrieve Top-K chunks, render prompt, call LLM,
parse the structured action guide.

The pipeline keeps multiple fallback paths so the API can return a sane
payload even when the retrieval is weak, the LLM stalls, or the LLM
provider is unreachable (AI-16):

- weak retrieval (all hits below `similarity_threshold`) -> fallback msg
- LLM raised / returned no parseable steps                -> cached response if available
- LLM unreachable (ConnectionError)                       -> cached response if available
"""

from __future__ import annotations

import json
import logging
import re
import time
from dataclasses import dataclass
from pathlib import Path

from langchain_core.embeddings import Embeddings
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import HumanMessage, SystemMessage

from app.config import Settings, get_settings
from app.core import prompt_loader
from app.core.embeddings import get_embeddings
from app.core.llm import get_llm
from app.core.vectorstore import SearchResult, VectorStore
from app.schemas.search import GuideStep, RawChunk, SearchResponse, SourceRef

CACHED_RESPONSES_PATH = (
    Path(__file__).resolve().parents[2] / "data" / "cached_responses.json"
)

# A query that already names an error code wins the demo cache lookup.
_ERROR_CODE_RE = re.compile(r"\bE-\d{3}\b")

logger = logging.getLogger(__name__)

FALLBACK_MESSAGE = "관련 매뉴얼을 찾지 못했습니다"

# Qwen3-family models (qwen3.5:9b included) emit a long <think> block by
# default and Ollama strips it, leaving an empty `content`. The `/no_think`
# directive disables that mode for this call. Harmless on non-Qwen models.
_NO_THINK = SystemMessage(content="/no_think")

# `1. action ... (출처: file.pdf, p.12)`  — robust to spacing, ".pdf" optional
_STEP_RE = re.compile(
    r"^\s*(\d+)[.)]\s*(.+?)(?:\s*\(\s*출처\s*[::]\s*(?P<file>[^,]+?)\s*,\s*p\.?\s*(?P<page>\d+)\s*\))?\s*$",
    re.MULTILINE,
)


@dataclass
class RagPipeline:
    settings: Settings
    embedder: Embeddings
    llm: BaseChatModel
    store: VectorStore

    @classmethod
    def build(cls, settings: Settings | None = None) -> "RagPipeline":
        settings = settings or get_settings()
        return cls(
            settings=settings,
            embedder=get_embeddings(settings),
            llm=get_llm(settings),
            store=VectorStore(settings),
        )

    # ----- public surface -----

    def search(
        self,
        query: str,
        *,
        equipment_id: str | None = None,
        top_k: int | None = None,
    ) -> SearchResponse:
        t0 = time.perf_counter()

        # 1) retrieve
        try:
            qvec = self.embedder.embed_query(query)
            chunks = self.store.similarity_search(
                qvec,
                k=top_k or self.settings.retrieval_top_k,
                equipment_id=equipment_id,
            )
        except ConnectionError as exc:
            # Embedding backend down — try the demo cache before bailing.
            cached = self._cache_lookup(query)
            if cached:
                return self._cached_response(cached, t0, reason="embed_unreachable")
            raise

        # 2) gating: similarity threshold (drop weak hits before LLM)
        kept = [c for c in chunks if c.similarity >= self.settings.similarity_threshold]
        if not kept:
            answer = FALLBACK_MESSAGE
            steps: list[GuideStep] = []
            fallback = True
        else:
            # 3) prompt + LLM (with cache fallback on hard failure)
            context = self._format_context(kept)
            prompt = prompt_loader.render("action_guide", context=context, query=query)
            try:
                # `/no_think` must appear in BOTH the system role AND the
                # start of the user content for qwen3.5:9b to skip its
                # default thinking block reliably (system-only is honoured
                # for short prompts but ignored once the user content
                # carries a long context).
                answer = self.llm.invoke(
                    [_NO_THINK, HumanMessage(content=f"/no_think\n\n{prompt}")]
                ).content
            except ConnectionError:
                cached = self._cache_lookup(query)
                if cached:
                    logger.warning("LLM unreachable; serving cached response")
                    return self._cached_response(cached, t0, reason="llm_unreachable")
                raise
            steps = self._parse_steps(answer)
            # Treat the response as a real answer when at least one cited
            # step parsed out — even if the model echoed the fallback line
            # at the end. Fallback is only when we have *nothing* useful.
            fallback = not steps

        latency_ms = int((time.perf_counter() - t0) * 1000)
        return SearchResponse(
            steps=steps,
            raw_chunks=[
                RawChunk(
                    chunk_id=c.chunk_id,
                    manual_id=c.manual_id,
                    equipment_id=c.equipment_id,
                    page=c.page,
                    chunk_text=c.chunk_text,
                    similarity=round(c.similarity, 4),
                )
                for c in chunks
            ],
            answer_text=answer,
            fallback=fallback,
            latency_ms=latency_ms,
        )

    # ----- helpers -----

    # Per-chunk context truncation. Local 9B model latency grows non-linearly
    # with input tokens; 600 chars × top_k≈3 keeps the prompt small enough
    # for the dev machine to respond within 60s without losing the cited page.
    _MAX_CHUNK_CHARS_FOR_PROMPT = 600

    def _cache_lookup(self, query: str) -> dict | None:
        """Return a frozen response for the error code in `query`, if any."""
        if not CACHED_RESPONSES_PATH.exists():
            return None
        m = _ERROR_CODE_RE.search(query)
        if not m:
            return None
        try:
            cache = json.loads(CACHED_RESPONSES_PATH.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            logger.error("cached_responses.json unreadable: %s", exc)
            return None
        return cache.get(m.group(0))

    def _cached_response(
        self,
        cached: dict,
        t0: float,
        *,
        reason: str,
    ) -> SearchResponse:
        latency_ms = int((time.perf_counter() - t0) * 1000)
        steps = [GuideStep(**s) for s in cached.get("steps", [])]
        raw_chunks = [RawChunk(**c) for c in cached.get("raw_chunks", [])]
        return SearchResponse(
            steps=steps,
            raw_chunks=raw_chunks,
            answer_text=cached.get("answer_text", "") + f"\n\n[cached: {reason}]",
            fallback=not steps,
            latency_ms=latency_ms,
        )

    def _format_context(self, chunks: list[SearchResult]) -> str:
        blocks = []
        for c in chunks:
            text = c.chunk_text[: self._MAX_CHUNK_CHARS_FOR_PROMPT]
            blocks.append(
                f"[매뉴얼: {c.manual_id}.pdf, 페이지: {c.page}]\n{text}"
            )
        return "\n\n---\n\n".join(blocks)

    def _parse_steps(self, text: str) -> list[GuideStep]:
        steps: list[GuideStep] = []
        for m in _STEP_RE.finditer(text):
            order = int(m.group(1))
            action = m.group(2).strip()
            file_, page = m.group("file"), m.group("page")
            source = (
                SourceRef(manual=file_.strip(), page=int(page)) if file_ and page else None
            )
            steps.append(GuideStep(order=order, action=action, source=source))
        return steps
