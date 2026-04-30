"""Unit tests for the LLM and embedding factories.

We intentionally do NOT make network calls to Ollama or OpenAI here. The
contract under test is: given an env config, the factory returns a client
of the correct provider class with the configured model. The actual call
path is exercised by integration tests later.
"""

from __future__ import annotations

import pytest

from app.config import Settings
from app.core.embeddings import get_embeddings
from app.core.llm import get_llm


def _settings(**overrides) -> Settings:
    base = dict(
        llm_provider="ollama",
        ollama_base_url="http://localhost:11434",
        ollama_model="qwen3.5:9b",
        openai_api_key="sk-test",
        openai_model="gpt-4o-mini",
        embedding_provider="ollama",
        embedding_model="bge-m3",
        openai_embedding_model="text-embedding-3-small",
    )
    base.update(overrides)
    return Settings(**base)


# ---------- LLM ----------

def test_get_llm_ollama_returns_chatollama():
    from langchain_ollama import ChatOllama

    llm = get_llm(_settings(llm_provider="ollama"))
    assert isinstance(llm, ChatOllama)
    assert llm.model == "qwen3.5:9b"


def test_get_llm_openai_returns_chatopenai():
    from langchain_openai import ChatOpenAI

    llm = get_llm(_settings(llm_provider="openai"))
    assert isinstance(llm, ChatOpenAI)
    assert llm.model_name == "gpt-4o-mini"


def test_get_llm_openai_requires_api_key():
    with pytest.raises(RuntimeError, match="OPENAI_API_KEY"):
        get_llm(_settings(llm_provider="openai", openai_api_key=None))


def test_get_llm_unknown_provider_rejected():
    # bypass Literal validation by constructing the model with model_construct
    s = _settings()
    object.__setattr__(s, "llm_provider", "anthropic")
    with pytest.raises(ValueError, match="Unsupported LLM_PROVIDER"):
        get_llm(s)


# ---------- Embeddings ----------

def test_get_embeddings_ollama_returns_ollama_embeddings():
    from langchain_ollama import OllamaEmbeddings

    emb = get_embeddings(_settings(embedding_provider="ollama"))
    assert isinstance(emb, OllamaEmbeddings)
    assert emb.model == "bge-m3"


def test_get_embeddings_openai_returns_openai_embeddings():
    from langchain_openai import OpenAIEmbeddings

    emb = get_embeddings(_settings(embedding_provider="openai"))
    assert isinstance(emb, OpenAIEmbeddings)
    assert emb.model == "text-embedding-3-small"


def test_get_embeddings_openai_requires_api_key():
    with pytest.raises(RuntimeError, match="OPENAI_API_KEY"):
        get_embeddings(_settings(embedding_provider="openai", openai_api_key=None))
