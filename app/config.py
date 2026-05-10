from functools import lru_cache
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = "agentic-knowledge-assistant"
    environment: str = "local"
    log_level: str = "INFO"

    postgres_host: str = "localhost"
    postgres_port: int = 5432
    postgres_db: str = "agentic_knowledge"
    postgres_user: str = "agentic"
    postgres_password: str = Field(default="agentic")

    embedding_provider: Literal["auto", "fake", "openai"] = "auto"
    embedding_dimensions: int = 1536
    embedding_model: str = "text-embedding-3-small"
    embedding_include_dimensions: bool = True
    embedding_request_timeout_seconds: float = 30.0

    chunk_size_tokens: int = 900
    chunk_overlap_tokens: int = 120

    openai_api_key: str | None = None
    openai_base_url: str | None = None

    @property
    def database_url(self) -> str:
        return (
            "postgresql+psycopg://"
            f"{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )


@lru_cache
def get_settings() -> Settings:
    return Settings()
