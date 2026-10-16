from pathlib import Path
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=Path(__file__).resolve().with_name(".env"), extra="ignore")

    database_url: str = "postgresql+asyncpg://taxora:taxora@localhost:5432/taxora"
    admin_token: str = Field(min_length=32)
    auth_secret_key: str = Field(min_length=32)
    auth_cookie_secure: bool = False
    auth_cookie_name: str = "taxora_session"
    auth_cookie_samesite: Literal["lax", "strict", "none"] = "lax"
    auth_session_minutes: int = 60
    openai_api_key: str = ""
    llm_model: str = "gpt-4o-mini"
    embedding_model: str = "text-embedding-3-small"
    embedding_dimensions: int = 1536
    retrieval_top_k: int = 5
    max_upload_bytes: int = 10 * 1024 * 1024
    frontend_origin: str = "http://localhost:5173"


settings = Settings()
