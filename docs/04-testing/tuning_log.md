# RAG Tuning Log

Chronological record of retrieval-tuning experiments. Each row is a deliberate change we tried, with the hypothesis and the measured outcome — so we can roll back or pick up a thread later.

| Date | Change | Hypothesis | Result | Decision |
|---|---|---|---|---|
| 2026-04-30 | Baseline: bge-m3 + 800/100 chunking + Top-3 + HNSW cosine, no metadata filter | Synthetic manuals are deterministic enough for naive retrieval | **100.0% (25/25)** on `test_set.json`, avg retrieval 1078 ms | **Adopted as the M3 KPI baseline.** No further tuning needed. |

If accuracy falls below 80% in future runs (regenerated manuals, real OEM PDFs, larger eval set, etc.), append a row here before changing the code so the experiment trail stays linear.
