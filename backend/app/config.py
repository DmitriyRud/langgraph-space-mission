from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    llm_provider: Literal["ollama", "openai_compatible"] = "ollama"
    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "qwen3:4b"
    llm_temperature: float = 0.2
    llm_timeout_seconds: float = 60.0
    llm_max_concurrency: int = 1

    openai_base_url: str = "https://api.openai.com/v1"
    openai_api_key: str = ""
    openai_model: str = "gpt-4o-mini"

    database_dir: str = "./data"
    cors_origins: str = "http://localhost:5173,http://127.0.0.1:5173"
    default_max_iterations: int = 5

    @property
    def data_path(self) -> Path:
        path = Path(self.database_dir)
        path.mkdir(parents=True, exist_ok=True)
        return path

    @property
    def checkpoints_db_path(self) -> Path:
        return self.data_path / "langgraph_checkpoints.db"

    @property
    def events_db_path(self) -> Path:
        return self.data_path / "mission_events.db"

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
