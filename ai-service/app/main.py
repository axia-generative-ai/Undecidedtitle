from __future__ import annotations

import logging
import os

from fastapi import FastAPI

from app.api.anomaly import router as anomaly_router
from app.api.search import router as search_router

logger = logging.getLogger(__name__)
logging.basicConfig(level=os.getenv("LOG_LEVEL", "INFO"))

app = FastAPI(
    title="FactoryGuard AI Service",
    version="0.1.0",
    description="Equipment manual RAG and anomaly analysis API.",
)

app.include_router(search_router)
app.include_router(anomaly_router)


@app.on_event("startup")
def _warmup_embedder() -> None:
    """Page the embedding model into Ollama memory at startup.

    Without this, the *first* request after Ollama unloads the model
    (default idle timeout 5 min) pays a 2 s+ retrieval cost. The latency
    benchmark P95 fails over this exact spike. We discard the result —
    we only care that the model is hot.
    """
    try:
        from app.core.embeddings import get_embeddings

        get_embeddings().embed_query("warmup")
        logger.info("embedder warmed up at startup")
    except Exception as exc:  # noqa: BLE001 — startup must not crash the app
        logger.warning("embedder warmup failed: %s", exc)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


def main() -> None:
    import uvicorn

    uvicorn.run(
        "app.main:app",
        host=os.getenv("HOST", "0.0.0.0"),
        port=int(os.getenv("PORT", "8000")),
        reload=False,
    )


if __name__ == "__main__":
    main()
