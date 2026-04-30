"""Centralised application settings.

All runtime configuration must be loaded through `get_settings()`. Modules
must not read environment variables directly — go through this module so the
provider-swap contract (Ollama <-> OpenAI) stays enforceable.
"""

from __future__ import annotations

from functools import lru_cache
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

LLMProvider = Literal["ollama", "openai"]
EmbeddingProvider = Literal["ollama", "openai"]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    # ---- LLM ----
    llm_provider: LLMProvider = "ollama"
    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "qwen3.5:9b"
    openai_api_key: str | None = None
    openai_model: str = "gpt-4o-mini"

    # ---- Embeddings ----
    embedding_provider: EmbeddingProvider = "ollama"
    embedding_model: str = "bge-m3"
    openai_embedding_model: str = "text-embedding-3-small"

    # ---- Database ----
    database_url: str = (
        "postgresql+psycopg://factoryguard:factoryguard@localhost:5432/factoryguard"
    )

    # ---- Server ----
    host: str = "0.0.0.0"
    port: int = 8000
    log_level: str = "INFO"

    # ---- Pipeline tuning (used in later phases) ----
    chunk_size: int = Field(default=800, ge=100)
    chunk_overlap: int = Field(default=100, ge=0)
    retrieval_top_k: int = Field(default=3, ge=1)
    similarity_threshold: float = Field(default=0.3, ge=0.0, le=1.0)


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return the singleton settings instance.

    Tests can clear the cache via `get_settings.cache_clear()` after
    monkeypatching environment variables.
    """
    return Settings()
