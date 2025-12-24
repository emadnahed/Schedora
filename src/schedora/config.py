"""Configuration management for Schedora."""
from functools import lru_cache
from typing import Optional
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    Application settings loaded from environment variables.

    All settings can be overridden via environment variables.
    Required variables must be set, optional ones have defaults.
    """

    # Application
    APP_NAME: str = "Schedora"
    APP_VERSION: str = "0.1.0"
    DEBUG: bool = False
    ENVIRONMENT: str = "development"

    # Database
    DATABASE_URL: str
    DATABASE_POOL_SIZE: int = 5
    DATABASE_MAX_OVERFLOW: int = 10
    DATABASE_ECHO: bool = False

    # Redis
    REDIS_URL: str = "redis://localhost:6379/0"
    REDIS_DB: int = 0

    # API
    API_V1_PREFIX: str = "/api/v1"

    # Testing
    TEST_DATABASE_URL: Optional[str] = None

    # Worker heartbeat configuration
    WORKER_HEARTBEAT_INTERVAL: int = 30  # Seconds between heartbeats
    WORKER_HEARTBEAT_TIMEOUT: int = 90  # Seconds before worker considered stale
    WORKER_STALE_CHECK_INTERVAL: int = 60  # Seconds between stale worker checks
    WORKER_CLEANUP_AFTER: int = 3600  # Seconds before removing stopped workers

    model_config = SettingsConfigDict(
        env_file=".env",
        case_sensitive=True,
        extra="ignore",
    )


@lru_cache()
def get_settings() -> Settings:
    """
    Get cached settings instance.

    Returns:
        Settings: Singleton settings instance
    """
    return Settings()
