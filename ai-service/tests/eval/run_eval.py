"""KPI evaluation runner (AI-13).

Runs every case in `test_set.json` against the **retrieval** half of the
RAG pipeline only. Per WBS AI-14, the M3 KPI is

    Top-3 retrieval contains expected_manual_id AND at least one
    expected_page is among the retrieved chunks  >= 80%.

So this script intentionally skips the LLM call — it would add minutes
per case and the KPI cannot fail or pass on the LLM step. Anyone who
wants to score the LLM output separately can wire that in later.

CLI:
    uv run python tests/eval/run_eval.py
    uv run python tests/eval/run_eval.py --output tests/eval/results/run.json
    uv run python tests/eval/run_eval.py --threshold 0.8

Exit code:
    0  accuracy >= threshold
    1  accuracy <  threshold
    2  setup error (missing files etc.)
"""

from __future__ import annotations

import argparse
import csv
import json
import logging
import sys
import time
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path

from app.core.embeddings import get_embeddings
from app.core.vectorstore import VectorStore

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_TEST_SET = ROOT / "tests" / "eval" / "test_set.json"
DEFAULT_RESULTS_DIR = ROOT / "tests" / "eval" / "results"

log = logging.getLogger("run_eval")
logging.basicConfig(level="INFO", format="%(levelname)s %(message)s")


@dataclass
class CaseResult:
    case_id: str
    query: str
    error_code: str
    expected_manual_id: str
    expected_pages: list[int]
    retrieved: list[dict]      # [{manual_id, page, similarity}]
    manual_match: bool
    page_match: bool
    correct: bool              # manual_match AND page_match
    retrieval_ms: int


def _is_correct(case: dict, retrieved: list[dict]) -> tuple[bool, bool]:
    expected_manual = case["expected_manual_id"]
    expected_pages = set(case["expected_pages"])
    manual_match = any(r["manual_id"] == expected_manual for r in retrieved)
    page_match = any(
        r["manual_id"] == expected_manual and r["page"] in expected_pages
        for r in retrieved
    )
    return manual_match, page_match


def run(
    test_set_path: Path,
    *,
    top_k: int,
    threshold: float,
) -> tuple[list[CaseResult], dict]:
    if not test_set_path.exists():
        log.error("test set not found: %s", test_set_path)
        sys.exit(2)
    cases = json.loads(test_set_path.read_text(encoding="utf-8"))

    embedder = get_embeddings()
    store = VectorStore()

    results: list[CaseResult] = []
    correct_count = 0
    total_retrieval_ms = 0

    for case in cases:
        t0 = time.perf_counter()
        qvec = embedder.embed_query(case["natural_language_query"])
        chunks = store.similarity_search(qvec, k=top_k)
        rt_ms = int((time.perf_counter() - t0) * 1000)

        retrieved = [
            {
                "manual_id": c.manual_id,
                "page": c.page,
                "similarity": round(c.similarity, 4),
            }
            for c in chunks
        ]
        manual_match, page_match = _is_correct(case, retrieved)
        correct = manual_match and page_match
        if correct:
            correct_count += 1

        results.append(
            CaseResult(
                case_id=case["id"],
                query=case["natural_language_query"],
                error_code=case["error_code"],
                expected_manual_id=case["expected_manual_id"],
                expected_pages=case["expected_pages"],
                retrieved=retrieved,
                manual_match=manual_match,
                page_match=page_match,
                correct=correct,
                retrieval_ms=rt_ms,
            )
        )
        total_retrieval_ms += rt_ms
        marker = "OK " if correct else "MISS"
        log.info(
            "%s %s [%s] -> %s | retrieved=%s | %dms",
            marker,
            case["id"],
            case["error_code"],
            "manual+page" if correct else (
                "manual-only" if manual_match else "no-manual"
            ),
            [(r["manual_id"], r["page"]) for r in retrieved],
            rt_ms,
        )

    n = len(cases)
    accuracy = correct_count / n if n else 0.0
    summary = {
        "test_set": str(test_set_path),
        "ran_at": datetime.now(timezone.utc).isoformat(),
        "total_cases": n,
        "correct": correct_count,
        "accuracy": round(accuracy, 4),
        "kpi_threshold": threshold,
        "kpi_pass": accuracy >= threshold,
        "top_k": top_k,
        "avg_retrieval_ms": round(total_retrieval_ms / n, 1) if n else 0.0,
    }
    return results, summary


def write_reports(results: list[CaseResult], summary: dict, out_path: Path) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(
        json.dumps(
            {"summary": summary, "cases": [asdict(r) for r in results]},
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    csv_path = out_path.with_suffix(".csv")
    with csv_path.open("w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(
            [
                "case_id", "error_code", "expected_manual_id",
                "expected_pages", "retrieved", "manual_match",
                "page_match", "correct", "retrieval_ms",
            ]
        )
        for r in results:
            w.writerow([
                r.case_id, r.error_code, r.expected_manual_id,
                "|".join(map(str, r.expected_pages)),
                "|".join(f"{x['manual_id']}:p{x['page']}" for x in r.retrieved),
                int(r.manual_match), int(r.page_match), int(r.correct),
                r.retrieval_ms,
            ])
    log.info("wrote %s", out_path.relative_to(ROOT))
    log.info("wrote %s", csv_path.relative_to(ROOT))


def main() -> None:
    ap = argparse.ArgumentParser(description="FactoryGuard RAG eval runner")
    ap.add_argument("--test-set", type=Path, default=DEFAULT_TEST_SET)
    ap.add_argument(
        "--output",
        type=Path,
        default=None,
        help="result JSON path (defaults to results/<timestamp>.json)",
    )
    ap.add_argument("--top-k", type=int, default=3, help="retrieval Top-K (default 3)")
    ap.add_argument("--threshold", type=float, default=0.8, help="KPI threshold (default 0.8)")
    args = ap.parse_args()

    if args.output is None:
        ts = datetime.now().strftime("%Y%m%d-%H%M%S")
        args.output = DEFAULT_RESULTS_DIR / f"{ts}.json"

    results, summary = run(
        args.test_set,
        top_k=args.top_k,
        threshold=args.threshold,
    )
    write_reports(results, summary, args.output)

    log.info(
        "accuracy = %.1f%% (%d/%d), KPI %s @ %.0f%% (avg retrieval %.0fms)",
        summary["accuracy"] * 100,
        summary["correct"],
        summary["total_cases"],
        "PASS" if summary["kpi_pass"] else "FAIL",
        summary["kpi_threshold"] * 100,
        summary["avg_retrieval_ms"],
    )

    sys.exit(0 if summary["kpi_pass"] else 1)


if __name__ == "__main__":
    main()
