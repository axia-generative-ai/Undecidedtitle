"""Unit tests for the embedding pipeline.

Uses a fake `Embeddings` implementation so the test does not touch Ollama
or OpenAI.
"""

from __future__ import annotations

from langchain_core.embeddings import Embeddings

from app.pipelines.chunking import Chunk
from app.pipelines.embedding import embed_chunks, embedding_dimension


class _FakeEmbeddings(Embeddings):
    def __init__(self, dim: int = 8) -> None:
        self.dim = dim
        self.calls: list[int] = []

    def embed_documents(self, texts):
        self.calls.append(len(texts))
        return [[float(i)] * self.dim for i, _ in enumerate(texts)]

    def embed_query(self, text):
        return [0.0] * self.dim


def _chunk(i: int) -> Chunk:
    return Chunk(
        chunk_id=f"id-{i}",
        manual_id="fixture",
        equipment_id="eq_test",
        page=1,
        chunk_index=i,
        chunk_text=f"text-{i}",
        source_file="fixture.pdf",
    )


def test_embed_chunks_returns_pairs():
    fake = _FakeEmbeddings(dim=4)
    chunks = [_chunk(i) for i in range(5)]
    pairs = embed_chunks(chunks, embedder=fake, batch_size=2)
    assert len(pairs) == 5
    assert all(len(v) == 4 for _, v in pairs)
    # batched as 2,2,1
    assert fake.calls == [2, 2, 1]


def test_embed_chunks_empty():
    fake = _FakeEmbeddings()
    assert embed_chunks([], embedder=fake) == []
    assert fake.calls == []


def test_embedding_dimension_probe():
    assert embedding_dimension(_FakeEmbeddings(dim=11)) == 11
