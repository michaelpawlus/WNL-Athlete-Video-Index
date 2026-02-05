"""Application settings using Pydantic BaseSettings."""
from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application configuration loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Anthropic API
    anthropic_api_key: str = ""

    # Database
    database_url: str = "sqlite:///data/wnl_athlete_video_index.db"

    # Claude model
    claude_model: str = "claude-sonnet-4-20250514"


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()
