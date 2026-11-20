from pathlib import Path
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

BACKEND_DIR = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=BACKEND_DIR / ".env", extra="ignore")

    app_env: Literal["development", "test", "production"] = "development"
    log_level: str = "INFO"

    database_url: str = "postgresql+asyncpg://taxora:taxora@localhost:5432/taxora"
    auth_secret_key: str = Field(min_length=32)
    auth_cookie_secure: bool = False
    auth_cookie_name: str = "taxora_session"
    auth_cookie_samesite: Literal["lax", "strict", "none"] = "lax"
    auth_session_minutes: int = 60
    # Per client IP; see app/core/rate_limit.py for the single-process limitation.
    auth_login_attempts_per_minute: int = 10
    auth_registrations_per_hour: int = 5

    # LLM: any OpenAI-compatible chat API. Defaults to OpenRouter's free-model router.
    llm_api_key: str = ""
    llm_base_url: str = "https://openrouter.ai/api/v1"
    llm_model: str = "openrouter/free"
    llm_timeout_seconds: float = 45
    llm_max_output_tokens: int = 1500
    # OpenRouter only: route to providers that neither retain nor train on prompts.
    llm_zero_data_retention: bool = True

    # Embeddings run locally (fastembed); changing the model requires re-indexing all chunks.
    embedding_model: str = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
    embedding_dimensions: int = 384

    # Retrieval and chat safety. Thresholds are initial values and must be re-tuned on the
    # evaluation dataset (PRD §11) whenever the embedding model or knowledge base changes.
    retrieval_top_k: int = 5
    retrieval_max_cosine_distance: float = 0.7  # not yet calibrated: no indexed documents
    scope_min_similarity: float = 0.25  # calibrated on 16 sample questions only
    chat_requests_per_hour: int = 20

    max_upload_bytes: int = 10 * 1024 * 1024
    frontend_origin: str = "http://localhost:5173"


settings = Settings()
