"""LLM factory.

The single allowed entrypoint for chat-model construction in this codebase.
Business logic must import `get_llm()` from here; never instantiate provider
SDK classes directly. This is what makes the demo-day Ollama -> OpenAI swap
a one-line `.env` change.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from app.config import Settings, get_settings

if TYPE_CHECKING:
    from langchain_core.language_models.chat_models import BaseChatModel


def get_llm(settings: Settings | None = None) -> "BaseChatModel":
    """Return a LangChain chat model selected by `LLM_PROVIDER`."""
    settings = settings or get_settings()
    provider = settings.llm_provider

    if provider == "ollama":
        from langchain_ollama import ChatOllama

        return ChatOllama(
            base_url=settings.ollama_base_url,
            model=settings.ollama_model,
            temperature=0.0,
        )

    if provider == "openai":
        if not settings.openai_api_key:
            raise RuntimeError(
                "LLM_PROVIDER=openai but OPENAI_API_KEY is not set."
            )
        from langchain_openai import ChatOpenAI

        return ChatOpenAI(
            api_key=settings.openai_api_key,
            model=settings.openai_model,
            temperature=0.0,
        )

    raise ValueError(f"Unsupported LLM_PROVIDER: {provider!r}")
