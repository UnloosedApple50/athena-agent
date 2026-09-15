"""Configuration management for Athena Agent."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_prefix="ATHENA_",
        case_sensitive=False,
        extra="ignore",
    )

    # Server
    host: str = "0.0.0.0"
    port: int = 8585

    # Database
    db_path: str = "./data/athena.db"

    # LLM
    llm_base_url: str = "http://localhost:11434/v1"
    llm_model: str = "llama3.2"
    llm_timeout: int = 30
    llm_api_key: str = "ollama"  # Ollama doesn't need a real key

    # Logging
    log_level: str = "INFO"

    # Memory
    max_memory: int = 10000
    working_memory_size: int = 20

    # Security
    max_input_length: int = 10000
    rate_limit: int = 100  # requests per minute

    @property
    def db_path_resolved(self) -> Path:
        """Return resolved database path."""
        return Path(self.db_path).resolve()


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()
