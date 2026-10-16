from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "postgresql+asyncpg://taxora:taxora@localhost:5432/taxora"
    api_token: str = "change-me-for-local-development"
    admin_token: str = "change-me-admin"
    openai_api_key: str = ""
    llm_model: str = "gpt-4o-mini"
    embedding_model: str = "text-embedding-3-small"
    embedding_dimensions: int = 1536
    retrieval_top_k: int = 5
    max_upload_bytes: int = 10 * 1024 * 1024
    frontend_origin: str = "http://localhost:3000"


settings = Settings()
