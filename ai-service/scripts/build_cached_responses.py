"""Pre-compute fallback responses for the demo path (AI-16).

Builds `data/cached_responses.json` keyed by error_code so the API can
serve a known-good answer when the LLM provider is unreachable. Pulls
the same RAG context the live pipeline would, runs the LLM once per
target code, parses the steps, and freezes the result.

Run:
    uv run python scripts/build_cached_responses.py
"""

from __future__ import annotations

import json
import logging
import time
from pathlib import Path

from app.pipelines.rag import RagPipeline

ROOT = Path(__file__).resolve().parents[1]
ERR_CODES = ROOT / "data" / "error_codes.json"
OUT = ROOT / "data" / "cached_responses.json"

# WBS AI-16: pre-generate at least 10 codes for the demo backup path.
# We pick one per equipment, then top up to 10 with the most severe ones.
DEMO_CODES = [
    "E-204",  # pv300 — actuator timeout
    "E-301",  # cv550 — overcurrent (critical)
    "E-302",  # cv550 — bearing vibration (paraphrase test target)
    "E-401",  # hp120 — pressure drop (critical)
    "E-402",  # hp120 — oil overheat
    "E-403",  # hp120 — light curtain fail (critical)
    "E-501",  # rb900 — collision detected
    "E-503",  # rb900 — safety input broken (critical)
    "E-601",  # cn450 — spindle overload
    "E-603",  # cn450 — axis position deviation
]

logging.basicConfig(level="INFO", format="%(levelname)s %(message)s")
log = logging.getLogger("build_cached_responses")


def main() -> None:
    if not ERR_CODES.exists():
        raise SystemExit(f"missing {ERR_CODES}; run scripts/build_error_codes.py first")
    err_codes = {r["code"]: r for r in json.loads(ERR_CODES.read_text(encoding="utf-8"))}
    missing = [c for c in DEMO_CODES if c not in err_codes]
    if missing:
        raise SystemExit(f"unknown error codes in DEMO_CODES: {missing}")

    pipeline = RagPipeline.build()
    cache: dict[str, dict] = {}

    for code in DEMO_CODES:
        meta = err_codes[code]
        query = f"{code} 코드가 떴습니다. 어떻게 조치하나요?"
        log.info("priming %s (%s)", code, meta["equipment_name"])
        t = time.perf_counter()
        r = pipeline.search(query, equipment_id=meta["equipment_id"])
        elapsed = time.perf_counter() - t
        if r.fallback or not r.steps:
            log.warning("  -> fallback during priming for %s; storing raw_chunks only", code)
        cache[code] = {
            "error_code": code,
            "equipment_id": meta["equipment_id"],
            "equipment_name": meta["equipment_name"],
            "manual_filename": meta["manual_filename"],
            "expected_pages": meta["expected_pages"],
            "answer_text": r.answer_text,
            "steps": [s.model_dump() for s in r.steps],
            "raw_chunks": [c.model_dump() for c in r.raw_chunks],
            "primed_in_seconds": round(elapsed, 1),
        }

    OUT.write_text(json.dumps(cache, ensure_ascii=False, indent=2), encoding="utf-8")
    log.info("wrote %s (%d codes)", OUT.relative_to(ROOT), len(cache))


if __name__ == "__main__":
    main()
