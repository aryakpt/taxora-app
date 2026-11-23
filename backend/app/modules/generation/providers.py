"""Single place that builds AI providers. Callers use `providers.get_llm()` (module attribute
access) so tests can replace these functions with fakes."""

from functools import lru_cache

from app.core.config import settings
from app.modules.generation.embeddings import ApiEmbedder, Embedder
from app.modules.generation.llm import LLMClient, OpenAICompatibleLLM


@lru_cache(maxsize=1)
def _configured_embedder() -> Embedder:
    return ApiEmbedder(
        settings.embedding_api_key or settings.llm_api_key, settings.embedding_base_url, settings.embedding_model,
        settings.embedding_dimensions, tokens_per_minute=settings.embedding_tokens_per_minute,
    )


def get_embedder() -> Embedder | None:
    """None without an API key: the scope guard then relies on tax terms only and search on keywords only."""
    return _configured_embedder() if (settings.embedding_api_key or settings.llm_api_key) else None


@lru_cache(maxsize=1)
def _configured_llm() -> LLMClient:
    return OpenAICompatibleLLM(settings.llm_api_key, settings.llm_base_url, settings.llm_model,
                               settings.llm_fallback_models)


def get_llm() -> LLMClient | None:
    """None when no API key is configured: the chat then reports that AI is unavailable."""
    return _configured_llm() if settings.llm_api_key else None
