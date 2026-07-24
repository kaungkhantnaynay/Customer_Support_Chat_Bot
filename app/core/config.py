from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "Customer Support AI"
    app_env: str = "development"
    openai_api_key: str = ""
    database_url: str = "sqlite+aiosqlite:///./data/dev.db"
    knowledge_base_dir: Path = Path("data/knowledge_base")
    log_level: str = "INFO"

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
