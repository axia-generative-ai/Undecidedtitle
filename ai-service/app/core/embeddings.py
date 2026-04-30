"""Embedding factory.

Counterpart to `app.core.llm`. All embedding access in this codebase must
go through `get_embeddings()`. The pgvector column dimension is provider-
dependent (bge-m3 = 1024, text-embedding-3-small = 1536); see AI-08.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from app.config import Settings, get_settings

if TYPE_CHECKING:
    from langchain_core.embeddings import Embeddings


def get_embeddings(settings: Settings | None = None) -> "Embeddings":
    """Return a LangChain embedding model selected by `EMBEDDING_PROVIDER`."""
    settings = settings or get_settings()
    provider = settings.embedding_provider

    if provider == "ollama":
        from langchain_ollama import OllamaEmbeddings

        return OllamaEmbeddings(
            base_url=settings.ollama_base_url,
            model=settings.embedding_model,
        )

    if provider == "openai":
        if not settings.openai_api_key:
            raise RuntimeError(
                "EMBEDDING_PROVIDER=openai but OPENAI_API_KEY is not set."
            )
        from langchain_openai import OpenAIEmbeddings

        return OpenAIEmbeddings(
            api_key=settings.openai_api_key,
            model=settings.openai_embedding_model,
        )

    raise ValueError(f"Unsupported EMBEDDING_PROVIDER: {provider!r}")
