# FactoryGuard AI Service

Equipment manual RAG (Retrieval-Augmented Generation) and anomaly analysis service for the FactoryGuard prototype.

> **Source of truth for tasks:** [`.claude/wbs_tasks.md`](./.claude/wbs_tasks.md) (Korean: [`.claude/wbs_tasks.ko.md`](./.claude/wbs_tasks.ko.md))

---

## Stack

| Layer | Choice |
| --- | --- |
| Runtime | Python 3.10+ |
| Web framework | FastAPI + Uvicorn |
| Package manager | [uv](https://github.com/astral-sh/uv) |
| LLM (production) | OpenAI — `gpt-4o-mini` |
| LLM (local dev only) | Ollama — `qwen3.5:9b` |
| Embedding (production) | OpenAI — `text-embedding-3-small` (1536-dim) |
| Embedding (local dev only) | Ollama — `bge-m3` (1024-dim) |
| Vector store | PostgreSQL + pgvector (HNSW) |
| Orchestration | LangChain |

> **LLM model note.** WBS v1.0 specifies `qwen3:8b`, but the development machine uses `qwen3.5:9b` (already pulled). Defaults in `.env.example` and `scripts/pull_models.sh` reflect this.

---

## Quick start

### 1. Install dependencies

```bash
cd ai-service
uv sync
```

### 2. Configure environment

```bash
cp .env.example .env
# edit .env if you need to swap providers
```

### 3. Pull local models (Ollama)

```bash
bash scripts/pull_models.sh
```

This pulls `qwen3.5:9b` (LLM) and `bge-m3` (embedding). Skip if you set `LLM_PROVIDER=openai` and `EMBEDDING_PROVIDER=openai`.

### 4. Run the service

```bash
uv run python -m app.main
# or, with auto-reload during development:
uv run uvicorn app.main:app --reload
```

Then verify:

```bash
curl http://localhost:8000/health
# -> {"status":"ok"}
```

---

## Project layout

```
ai-service/
├── app/
│   ├── main.py             # FastAPI entrypoint, /health
│   ├── config.py           # pydantic-settings (AI-02)
│   ├── core/               # llm.py, embeddings.py, vectorstore.py, prompts/
│   ├── pipelines/          # chunking.py, embedding.py, rag.py, anomaly.py
│   ├── api/                # search.py, anomaly.py
│   └── schemas/            # request/response models
├── data/                   # manuals (PDF), error_codes.json, anomaly_rules.json
├── migrations/             # SQL migrations for pgvector
├── scripts/                # pull_models.sh, ingest_manuals.py, init_db.py
├── tests/
│   ├── unit/
│   └── eval/               # KPI evaluation harness (AI-13)
├── pyproject.toml
└── .env.example
```

---

## Provider swap (Ollama ⇄ OpenAI)

All LLM and embedding access goes through `app/core/llm.py` and `app/core/embeddings.py`. Switching providers is **environment-only** — no code changes:

```bash
# Local development
LLM_PROVIDER=ollama
EMBEDDING_PROVIDER=ollama

# Demo / production
LLM_PROVIDER=openai
OPENAI_API_KEY=sk-...
EMBEDDING_PROVIDER=openai
```

> ⚠️ **Embedding dimension mismatch** is a common bug when swapping providers (`bge-m3` is 1024-dim, `text-embedding-3-small` is 1536-dim). The pgvector column type must match. See AI-08 in the WBS.

---

## Phase status

Tracked in `.claude/wbs_tasks.md`. Current progress is committed per-phase to the `ai/feat` family of branches.
