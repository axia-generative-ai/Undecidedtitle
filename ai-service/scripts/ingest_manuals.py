"""Ingest all manuals in data/manuals/ into the vectorstore.

Reads `data/error_codes.json` to discover (manual_filename -> equipment_id)
mappings, then chunks → embeds → inserts. Uses the same provider
abstractions as the live API path.

Run (after init_db.py):
    uv run python scripts/ingest_manuals.py
"""

from __future__ import annotations

import json
import logging
import time
from pathlib import Path

from app.core.vectorstore import VectorStore
from app.pipelines.chunking import chunk_pdf
from app.pipelines.embedding import embed_chunks

ROOT = Path(__file__).resolve().parents[1]
MANUAL_DIR = ROOT / "data" / "manuals"
ERR_CODES = ROOT / "data" / "error_codes.json"

logging.basicConfig(level="INFO", format="%(levelname)s %(message)s")
log = logging.getLogger("ingest")


def _manual_to_equipment() -> dict[str, str]:
    records = json.loads(ERR_CODES.read_text(encoding="utf-8"))
    return {r["manual_filename"]: r["equipment_id"] for r in records}


def main() -> None:
    if not ERR_CODES.exists():
        raise SystemExit(f"missing {ERR_CODES}; run scripts/build_error_codes.py first")
    mapping = _manual_to_equipment()
    pdfs = sorted(MANUAL_DIR.glob("*.pdf"))
    if not pdfs:
        raise SystemExit(f"no manuals in {MANUAL_DIR}; run scripts/generate_manuals.py first")

    store = VectorStore()
    store.truncate()  # idempotent reload

    start = time.perf_counter()
    total_chunks = 0
    for pdf in pdfs:
        equipment_id = mapping.get(pdf.name)
        if not equipment_id:
            log.warning("skipping %s — not in error_codes mapping", pdf.name)
            continue
        manual_id = pdf.stem
        log.info("chunking %s (equipment=%s)", pdf.name, equipment_id)
        chunks = chunk_pdf(pdf, manual_id=manual_id, equipment_id=equipment_id)
        log.info("  -> %d chunks; embedding...", len(chunks))
        pairs = embed_chunks(chunks)
        inserted = store.insert_chunks(pairs)
        log.info("  -> inserted %d", inserted)
        total_chunks += inserted

    elapsed = time.perf_counter() - start
    log.info(
        "ingest complete: %d chunks across %d manuals in %.1fs",
        total_chunks,
        len(pdfs),
        elapsed,
    )
    log.info("vectorstore row count: %d", store.count())


if __name__ == "__main__":
    main()
