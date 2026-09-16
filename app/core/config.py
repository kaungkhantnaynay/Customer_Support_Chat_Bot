from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "Customer Support AI"
    app_env: str = "development"
    # Compose-only settings are accepted when loading the shared .env file.
    postgres_password: str = Field(default="", repr=False, exclude=True)
    support_port: int = Field(default=8000, ge=1, le=65535)
    admin_username: str = "admin"
    admin_password: str = ""
    openai_api_key: str = ""
    vector_store: Literal["local", "pgvector"] = "local"
    ai_mode: Literal["offline", "openai"] = "offline"
    openai_chat_model: str = "gpt-5.4-mini"
    openai_embedding_model: str = "text-embedding-3-small"
    openai_timeout_seconds: float = Field(default=20, gt=0, le=120)
    semantic_min_score: float = Field(default=0.35, ge=0, le=1)
    semantic_high_score: float = Field(default=0.65, ge=0, le=1)
    history_message_limit: int = Field(default=6, ge=0, le=20)

    @model_validator(mode="after")
    def validate_ai_settings(self) -> "Settings":
        if self.ai_mode == "openai" and not self.openai_api_key.strip():
            raise ValueError("OPENAI_API_KEY is required when AI_MODE=openai.")
        if self.semantic_high_score < self.semantic_min_score:
            raise ValueError("Semantic high score must be at least the minimum score.")
        if self.vector_store == "pgvector":
            if self.ai_mode != "openai" or not self.database_url.startswith(
                ("postgres://", "postgresql://", "postgresql+psycopg://")
            ):
                raise ValueError("pgvector requires OpenAI mode and a PostgreSQL database URL.")
        return self

    database_url: str = "sqlite:///./data/dev.db"
    knowledge_base_dir: Path = Path("data/knowledge_base")
    log_level: str = "INFO"

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
