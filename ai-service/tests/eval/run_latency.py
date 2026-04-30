"""Latency benchmark for the end-to-end RAG pipeline (AI-15).

Calls `RagPipeline.search()` for every query in `test_set.json`, splits
the wall clock into retrieval (embedding + similarity_search) and
generation (LLM call), and reports mean / P50 / P95 / max in milliseconds.

CLI:
    uv run python tests/eval/run_latency.py
    uv run python tests/eval/run_latency.py --warmup 1 --output tests/eval/results/latency.json
"""

from __future__ import annotations

import argparse
import json
import logging
import statistics
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

from langchain_core.messages import HumanMessage, SystemMessage

from app.core import prompt_loader
from app.pipelines.rag import FALLBACK_MESSAGE, RagPipeline

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_TEST_SET = ROOT / "tests" / "eval" / "test_set.json"
DEFAULT_RESULTS_DIR = ROOT / "tests" / "eval" / "results"

log = logging.getLogger("run_latency")
logging.basicConfig(level="INFO", format="%(levelname)s %(message)s")

_NO_THINK = SystemMessage(content="/no_think")


def _measured_search(p: RagPipeline, query: str) -> dict[str, int | bool]:
    """Time-box each stage of one search separately."""
    t = time.perf_counter()
    qvec = p.embedder.embed_query(query)
    chunks = p.store.similarity_search(qvec, k=p.settings.retrieval_top_k)
    retrieval_ms = int((time.perf_counter() - t) * 1000)

    kept = [c for c in chunks if c.similarity >= p.settings.similarity_threshold]

    llm_ms = 0
    fallback = False
    if kept:
        context = p._format_context(kept)
        prompt = prompt_loader.render("action_guide", context=context, query=query)
        t = time.perf_counter()
        answer = p.llm.invoke(
            [_NO_THINK, HumanMessage(content=f"/no_think\n\n{prompt}")]
        ).content
        llm_ms = int((time.perf_counter() - t) * 1000)
        steps = p._parse_steps(answer)
        fallback = not steps
    else:
        fallback = True

    return {
        "retrieval_ms": retrieval_ms,
        "llm_ms": llm_ms,
        "total_ms": retrieval_ms + llm_ms,
        "fallback": fallback,
    }


def _percentile(xs: list[int], p: float) -> float:
    if not xs:
        return 0.0
    s = sorted(xs)
    k = (len(s) - 1) * p
    f = int(k)
    c = min(f + 1, len(s) - 1)
    return s[f] + (s[c] - s[f]) * (k - f)


def main() -> None:
    ap = argparse.ArgumentParser(description="FactoryGuard end-to-end latency bench")
    ap.add_argument("--test-set", type=Path, default=DEFAULT_TEST_SET)
    ap.add_argument("--output", type=Path, default=None)
    ap.add_argument("--warmup", type=int, default=1, help="warmup runs to discard")
    ap.add_argument("--threshold-s", type=float, default=6.0, help="P95 KPI in seconds")
    args = ap.parse_args()

    cases = json.loads(args.test_set.read_text(encoding="utf-8"))
    pipeline = RagPipeline.build()

    # Page both Ollama models into memory before the timed loop.
    # Without this, retrieval P95 is dominated by model load time
    # (2 s+ spikes on cold runs), even with one search-level warmup.
    log.info("priming embedder + LLM into Ollama memory")
    pipeline.embedder.embed_query("warmup")
    try:
        pipeline.llm.invoke("ping")
    except Exception as exc:  # noqa: BLE001
        log.warning("LLM warmup failed (continuing): %s", exc)

    # search-level warmup — first full path can still be slow
    for i in range(args.warmup):
        log.info("warmup %d/%d", i + 1, args.warmup)
        _measured_search(pipeline, cases[0]["natural_language_query"])

    samples: list[dict] = []
    for case in cases:
        m = _measured_search(pipeline, case["natural_language_query"])
        m["case_id"] = case["id"]
        m["query"] = case["natural_language_query"]
        samples.append(m)
        log.info(
            "%s retrieval=%dms llm=%dms total=%dms fallback=%s",
            case["id"], m["retrieval_ms"], m["llm_ms"], m["total_ms"], m["fallback"],
        )

    retrieval = [s["retrieval_ms"] for s in samples]
    llm = [s["llm_ms"] for s in samples]
    total = [s["total_ms"] for s in samples]
    p95_total_ms = _percentile(total, 0.95)

    summary = {
        "ran_at": datetime.now(timezone.utc).isoformat(),
        "n": len(samples),
        "warmup": args.warmup,
        "retrieval_ms": {
            "mean": round(statistics.fmean(retrieval), 1),
            "p50":  round(_percentile(retrieval, 0.50), 1),
            "p95":  round(_percentile(retrieval, 0.95), 1),
            "max":  max(retrieval),
        },
        "llm_ms": {
            "mean": round(statistics.fmean(llm), 1),
            "p50":  round(_percentile(llm, 0.50), 1),
            "p95":  round(_percentile(llm, 0.95), 1),
            "max":  max(llm),
        },
        "total_ms": {
            "mean": round(statistics.fmean(total), 1),
            "p50":  round(_percentile(total, 0.50), 1),
            "p95":  round(p95_total_ms, 1),
            "max":  max(total),
        },
        "kpi_p95_threshold_ms": int(args.threshold_s * 1000),
        "kpi_pass": p95_total_ms <= args.threshold_s * 1000,
        "fallback_count": sum(1 for s in samples if s["fallback"]),
    }

    if args.output is None:
        ts = datetime.now().strftime("%Y%m%d-%H%M%S")
        args.output = DEFAULT_RESULTS_DIR / f"latency-{ts}.json"
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps({"summary": summary, "samples": samples}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    log.info("wrote %s", args.output.relative_to(ROOT))
    log.info(
        "P95 total=%.0fms (KPI %.0fms %s) | retrieval p95=%.0fms | LLM p95=%.0fms",
        summary["total_ms"]["p95"],
        summary["kpi_p95_threshold_ms"],
        "PASS" if summary["kpi_pass"] else "FAIL",
        summary["retrieval_ms"]["p95"],
        summary["llm_ms"]["p95"],
    )
    sys.exit(0 if summary["kpi_pass"] else 1)


if __name__ == "__main__":
    main()
