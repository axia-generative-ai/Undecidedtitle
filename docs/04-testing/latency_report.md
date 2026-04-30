# RAG Latency Report

> **KPI**: P95 end-to-end latency ≤ **6 s** (PRD §5-1).
>
> **Result (2026-04-30, local Ollama qwen2.5:3b)**:
>
> | Run | Setup | Total P95 | KPI |
> |---|---|---:|---|
> | 1 | warmup-search only | 6973 ms | ❌ |
> | 2 | + explicit embedder/LLM priming before timing loop | 6480 ms | ❌ (–493 ms) |
>
> Both runs miss the 6 s P95 target by 480–970 ms. The mean and median
> are well inside KPI; only the long tail (Ollama re-loading models
> after a brief idle) pushes the percentile out.

---

## Setup

- Test set: `tests/eval/test_set.json` (25 cases).
- Pipeline: `RagPipeline.search()` end-to-end (embedding → pgvector → prompt → LLM → step parse).
- LLM: Ollama `qwen2.5:3b` running on this dev machine.
- Embedding: Ollama `bge-m3` (1024-dim).
- Vectorstore: PostgreSQL 17.9 + pgvector 0.8.x, HNSW cosine, 75 chunks.
- Warmup: 1 run (discarded).
- Runner: `uv run python tests/eval/run_latency.py`.

## Result summary (Run 2 — current best)

| Metric | Mean | P50 | P95 | Max |
|---|---:|---:|---:|---:|
| Retrieval (embed + similarity) | 734 ms | 462 ms | **2608 ms** | 2715 ms |
| LLM generation                | 3013 ms | 3474 ms | **5127 ms** | 5307 ms |
| **Total**                     | 3746 ms | 3755 ms | **6480 ms** | 7952 ms |

KPI threshold: 6000 ms (P95 total). Outcome: **FAIL** by 480 ms.

3 of 25 cases (eval_017 / 019 / 020) showed retrieval cold spikes of
2.4–2.7 s while every other case retrieved in 300–700 ms. These three
runs alone account for the P95 miss.

## Why P95 fails despite a healthy mean

The retrieval distribution is bimodal:

- **Hot path** (22 cases): retrieval 350–700 ms — model already paged in.
- **Cold spikes** (3 cases: eval_001, eval_019, eval_020): retrieval 2.4–2.6 s — Ollama re-loaded the embedding model after an idle pause.

If retrieval P95 were back at the hot-path level, total P95 would land near **5.4 s** and clear the KPI. The LLM stage (P95 5.2 s) is also tight: any added context length on the prompt would push the percentile over by itself.

## Mitigations applied so far

- ✅ **FastAPI startup warmup hook** (`app/main.py::_warmup_embedder`) pages the embedder before the first request.
- ✅ **Latency benchmark prime step** before the timing loop, calling both `embed_query` and `llm.invoke`.

These cut P95 by ~500 ms but did not pin the model long enough to cover all 25 sequential cases. Ollama still unloaded the embedder mid-run.

## Mitigations to apply for KPI compliance (in order of expected impact)

1. **Set `OLLAMA_KEEP_ALIVE=24h` on the Ollama server process** (NOT the FastAPI process — it is read by `ollama serve`). This is the cleanest fix and directly attacks the bimodal tail. With models pinned for the full bench window, retrieval P95 should return to ~700 ms and total P95 should land near **5.4 s**, comfortably under KPI.
2. **Reduce Top-K from 3 to 2 for the LLM context** (already supported via `Settings.retrieval_top_k`). Trims tokens fed to the LLM and shaves the LLM P95 by 0.5–1 s in our profile, with no accuracy loss observed in the AI-14 run (all expected pages already appear in Top-2).
3. **Demo-day swap to OpenAI.** `LLM_PROVIDER=openai` (`gpt-4o-mini`) responds in ~1–2 s for these prompts; the abstraction layer makes this an env-only change, no code touched.
4. **Cached responses (AI-16).** For the 10 demo error codes, we already pre-bake answers in `data/cached_responses.json`. When the live LLM is unreachable, `_cache_lookup` serves these instantly — meaning even a worst-case tail event ends in < 1 s for any cached query, which is what protects the demo path independent of the latency KPI.

## How to reproduce

```bash
cd ai-service
# (one-time) ensure DB ingest ran and Ollama models are pulled
uv run python tests/eval/run_latency.py
```

The runner exits non-zero when P95 exceeds the threshold, so CI can gate this KPI just like accuracy.
