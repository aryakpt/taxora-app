"""Single place that builds AI providers. Callers use `providers.get_llm()` (module attribute
access) so tests can replace these functions with fakes."""

from functools import lru_cache

from app.core.config import settings
from app.modules.generation.embeddings import Embedder, LocalEmbedder
from app.modules.generation.llm import LLMClient, OpenAICompatibleLLM


@lru_cache(maxsize=1)
def get_embedder() -> Embedder:
    return LocalEmbedder(settings.embedding_model)


@lru_cache(maxsize=1)
def _configured_llm() -> LLMClient:
    return OpenAICompatibleLLM(settings.llm_api_key, settings.llm_base_url, settings.llm_model,
                               settings.llm_fallback_models)


def get_llm() -> LLMClient | None:
    """None when no API key is configured: the chat then reports that AI is unavailable."""
    return _configured_llm() if settings.llm_api_key else None
