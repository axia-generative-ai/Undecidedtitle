# RAG Accuracy Report

> **KPI**: Top-3 retrieval contains `expected_manual_id` AND at least one
> `expected_page` is among the retrieved chunks  ≥ **80%**.
>
> **Result (2026-04-30)**: **100.0% (25/25)** — KPI **PASS** on the first run.

---

## Setup

- Test set: `tests/eval/test_set.json` (25 cases — 20 literal-code lookups + 5 natural-language paraphrases, derived from `data/error_codes.json`).
- Embedding: Ollama `bge-m3` (1024-dim).
- Vectorstore: PostgreSQL 17.9 + pgvector 0.8.x, HNSW cosine index, 75 chunks (5 manuals × 15 pages each).
- Top-K: 3.
- Runner: `uv run python tests/eval/run_eval.py`.

## Result

| Metric | Value |
|---|---|
| Total cases | 25 |
| Correct | 25 |
| Accuracy | **100.0%** |
| KPI threshold | 80.0% |
| KPI verdict | ✅ PASS |
| Avg retrieval latency | 1078 ms |

All 20 literal `E-XXX` queries and all 5 natural-language paraphrases retrieved at least one chunk from the correct manual on the correct page.

## Why no tuning was required

The synthetic manuals (`scripts/generate_manuals.py`) place each error-code detail on a dedicated page with the code in a clearly labelled heading. Combined with `bge-m3`'s strong multilingual recall, Top-3 retrieval converges on the correct manual deterministically.

If a future change (more error codes per page, real OEM manuals, OCR'd PDFs, etc.) drops accuracy below 80%, candidate knobs in order of impact:

1. **Chunk size / overlap** (`Settings.chunk_size`, `chunk_overlap`) — smaller chunks improve precision when several codes share a page.
2. **Equipment-id meta-filter** at query time — the API already supports `equipment_id` in `POST /api/v1/search` for in-product use; the eval harness deliberately does *not* pass it so the score reflects unscoped retrieval.
3. **Embedding model swap** — `EMBEDDING_PROVIDER=openai` (`text-embedding-3-small`, 1536-dim) typically lifts NL paraphrase recall further at the cost of an outbound API.

See `tuning_log.md` for the change log if any of those become necessary.

## How to reproduce

```bash
cd ai-service
uv run python scripts/init_db.py        # one-time, after Postgres install
uv run python scripts/ingest_manuals.py
uv run python tests/eval/run_eval.py
```

The runner exits non-zero when accuracy drops below the threshold so it can gate CI on this KPI.
