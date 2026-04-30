"""Batch embedding for chunked manual text.

All embedding access goes through `app.core.embeddings.get_embeddings()`
so the Ollama <-> OpenAI swap stays environment-only.
"""

from __future__ import annotations

import logging
import time
from collections.abc import Iterable, Sequence

from langchain_core.embeddings import Embeddings
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

from app.core.embeddings import get_embeddings
from app.pipelines.chunking import Chunk

logger = logging.getLogger(__name__)

DEFAULT_BATCH_SIZE = 32


@retry(
    reraise=True,
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=1, max=8),
    retry=retry_if_exception_type(Exception),
)
def _embed_batch(embedder: Embeddings, texts: Sequence[str]) -> list[list[float]]:
    return embedder.embed_documents(list(texts))


def embed_chunks(
    chunks: Iterable[Chunk],
    *,
    embedder: Embeddings | None = None,
    batch_size: int = DEFAULT_BATCH_SIZE,
) -> list[tuple[Chunk, list[float]]]:
    """Embed an iterable of chunks; returns (chunk, vector) pairs.

    Logs throughput (chunks/second) so AI-15 latency baselining can read
    the numbers from app logs without re-running embedding.
    """
    embedder = embedder or get_embeddings()
    chunk_list = list(chunks)
    if not chunk_list:
        return []

    results: list[tuple[Chunk, list[float]]] = []
    start = time.perf_counter()
    for i in range(0, len(chunk_list), batch_size):
        batch = chunk_list[i : i + batch_size]
        vectors = _embed_batch(embedder, [c.chunk_text for c in batch])
        if len(vectors) != len(batch):
            raise RuntimeError(
                f"embedding count mismatch: got {len(vectors)} for {len(batch)} chunks"
            )
        results.extend(zip(batch, vectors))

    elapsed = time.perf_counter() - start
    rate = len(chunk_list) / elapsed if elapsed > 0 else float("inf")
    dim = len(results[0][1]) if results else 0
    logger.info(
        "embedded chunks",
        extra={
            "count": len(chunk_list),
            "elapsed_s": round(elapsed, 2),
            "chunks_per_s": round(rate, 1),
            "dim": dim,
        },
    )
    return results


def embedding_dimension(embedder: Embeddings | None = None) -> int:
    """Probe the configured embedder for its output dimensionality.

    Used by the migration script and the vectorstore to size the
    pgvector column correctly.
    """
    embedder = embedder or get_embeddings()
    vec = embedder.embed_query("dimension probe")
    return len(vec)
