"""
Application configuration.

Loads settings from environment variables (and a local .env file during
development). Nothing here should ever contain a real secret — actual
values belong in a git-ignored `.env`, sourced from `.env.example`.
"""
from functools import lru_cache
from typing import List

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # --- App metadata ---
    app_name: str = "Clinical Trial Research Assistant"
    environment: str = "development"  # development | staging | production
    debug: bool = True

    # --- CORS ---
    # Comma-separated list of allowed origins, e.g. "http://localhost:5173,https://app.example.com"
    allowed_origins: str = "http://localhost:5173"

    # --- Firebase ---
    firebase_project_id: str = ""
    firebase_credentials_path: str = ""  # path to service account JSON (never committed)
    firebase_storage_bucket: str = ""

    # --- External APIs ---
    clinical_trials_api_base_url: str = "https://clinicaltrials.gov/api/v2"

    # --- AI / LLM ---
    ai_provider: str = "anthropic"  # abstraction layer selects provider from this
    anthropic_api_key: str = ""
    ai_model: str = "claude-sonnet-4-5"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    @property
    def allowed_origins_list(self) -> List[str]:
        return [origin.strip() for origin in self.allowed_origins.split(",") if origin.strip()]


@lru_cache
def get_settings() -> Settings:
    """Cached settings accessor — import and call this, don't instantiate Settings() directly."""
    return Settings()
