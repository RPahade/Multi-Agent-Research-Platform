"""Application configuration.

All settings are read from environment variables (and an optional local ``.env``
file) via pydantic-settings. This is the single import point for configuration
across the whole backend — never read ``os.environ`` directly elsewhere.
"""

from __future__ import annotations

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Typed application settings, populated from the environment."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # --- App metadata ---
    app_name: str = "Multi-Agent Research Intelligence Platform"
    app_version: str = "0.1.0"
    env: str = "development"
    log_level: str = "INFO"

    # --- API ---
    api_v1_prefix: str = "/api/v1"

    # Comma-separated list of origins allowed to call the API (Angular dev server, etc.)
    cors_origins: str = "http://localhost:4200"

    # --- Database ---
    # SQLAlchemy URL. Inside docker-compose the host is the ``db`` service.
    database_url: str = "postgresql+psycopg://postgres:postgres@db:5432/research"

    # --- Auth / JWT ---
    # Override in every real environment. Must be long & random.
    jwt_secret_key: str = "dev-only-insecure-secret-change-me-please-0123456789"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    refresh_token_expire_days: int = 7

    # --- First admin bootstrap (seeded on startup if set and not already present) ---
    first_admin_email: str | None = None
    first_admin_password: str | None = None
    first_admin_name: str = "Administrator"

    # --- Background jobs (Milestone 5) ---
    default_max_attempts: int = 3
    job_reaper_interval_seconds: int = 10
    job_heartbeat_stale_seconds: int = 30

    @property
    def cors_origins_list(self) -> list[str]:
        """Parse the comma-separated CORS origins into a clean list."""
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]


@lru_cache
def get_settings() -> Settings:
    """Return a cached ``Settings`` instance (built once per process)."""
    return Settings()


settings = get_settings()
