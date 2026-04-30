# RAG Evaluation Set

This directory contains the gold-standard evaluation set used to measure
the project's primary KPI.

## Files

- `test_set.json` — 25 evaluation cases (20 literal-code lookups + 5
  natural-language paraphrases) covering every error code in
  `data/error_codes.json`.
- `run_eval.py` *(forthcoming, AI-13)* — runs the cases against the RAG
  pipeline and emits an accuracy report.

## KPI

> **KPI: Top-3 contains `expected_manual_id` with at least one
> `expected_page` within retrieved chunks ≥ 80%.**

A case counts as **correct** when the Top-3 chunks returned by
`POST /api/v1/search` (or the underlying `similarity_search()`) satisfy
*both*:

1. at least one chunk's `manual_id` equals `expected_manual_id`, AND
2. at least one chunk's page number is in `expected_pages`.

Latency KPI is tracked separately (P95 ≤ 6s, see `docs/04-testing/latency_report.md`
once AI-15 lands).

## Schema (per case)

| Field | Type | Notes |
|---|---|---|
| `id` | string | `eval_001` … |
| `error_code` | string | `E-204` etc. |
| `equipment_id` | string | matches `data/error_codes.json` |
| `natural_language_query` | string | what the user asks |
| `expected_manual_id` | string | manual filename without `.pdf` |
| `expected_manual_filename` | string | original filename, for cross-check |
| `expected_pages` | int[] | one of these page numbers must appear in the Top-3 chunks |
| `notes` | string | rationale; flags paraphrase cases |

## Regenerate

The eval set is derived from `data/error_codes.json` so it never drifts:

```bash
uv run python scripts/build_eval_set.py
```

## How to run (forthcoming, AI-13)

```bash
uv run python tests/eval/run_eval.py \
  --test-set tests/eval/test_set.json \
  --output   tests/eval/results/$(date +%Y%m%d-%H%M%S).json
```

Exit code is non-zero when accuracy < 80% so CI can gate on it.
