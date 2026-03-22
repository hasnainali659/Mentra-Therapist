from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


PROJECT_ROOT = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    # OpenAI: embeddings + chat fallback when DeepSeek fails
    openai_api_key: str
    openai_embedding_model: str = "text-embedding-3-small"
    openai_model: str = "gpt-4o-mini"

    # Chat primary (DeepSeek, OpenAI-compatible API)
    deepseek_api_key: str
    deepseek_base_url: str = "https://api.deepseek.com"
    deepseek_model: str = "deepseek-chat"

    qdrant_url: str = "http://localhost:6333"
    qdrant_collection_name: str = "session_memories"
    sessions_dir: Path = PROJECT_ROOT / "sessions"

    model_config = SettingsConfigDict(
        env_file=PROJECT_ROOT / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()
