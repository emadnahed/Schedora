"""Unit tests for configuration management."""
import os
import pytest
from pydantic import ValidationError
from schedora.config import Settings, get_settings


class TestSettings:
    """Test Settings configuration class."""

    def test_settings_has_default_values(self):
        """Test Settings provides default values where applicable."""
        # Set required env vars for testing
        os.environ["DATABASE_URL"] = "postgresql://localhost/test"
        # Explicitly set DEBUG to false for this test
        os.environ["DEBUG"] = "false"

        settings = Settings()

        assert settings.APP_NAME == "Schedora"
        assert settings.APP_VERSION == "0.1.0"
        assert settings.DEBUG is False
        assert settings.ENVIRONMENT == "development"
        assert settings.API_V1_PREFIX == "/api/v1"

        # Cleanup
        del os.environ["DATABASE_URL"]
        if "DEBUG" in os.environ:
            del os.environ["DEBUG"]

    def test_settings_loads_database_url(self):
        """Test Settings loads DATABASE_URL from environment."""
        db_url = "postgresql://user:pass@localhost:5432/testdb"
        os.environ["DATABASE_URL"] = db_url

        settings = Settings()

        assert settings.DATABASE_URL == db_url

        # Cleanup
        del os.environ["DATABASE_URL"]

    def test_settings_redis_url_default(self):
        """Test Settings has default REDIS_URL."""
        os.environ["DATABASE_URL"] = "postgresql://localhost/test"

        settings = Settings()

        assert settings.REDIS_URL == "redis://localhost:6379/0"

        # Cleanup
        del os.environ["DATABASE_URL"]

    def test_settings_can_override_redis_url(self):
        """Test Settings can override REDIS_URL from environment."""
        os.environ["DATABASE_URL"] = "postgresql://localhost/test"
        os.environ["REDIS_URL"] = "redis://custom:6380/1"

        settings = Settings()

        assert settings.REDIS_URL == "redis://custom:6380/1"

        # Cleanup
        del os.environ["DATABASE_URL"]
        del os.environ["REDIS_URL"]

    def test_settings_database_pool_size_default(self):
        """Test Settings has default DATABASE_POOL_SIZE."""
        os.environ["DATABASE_URL"] = "postgresql://localhost/test"

        settings = Settings()

        assert settings.DATABASE_POOL_SIZE == 5
        assert settings.DATABASE_MAX_OVERFLOW == 10

        # Cleanup
        del os.environ["DATABASE_URL"]

    def test_get_settings_returns_cached_instance(self):
        """Test get_settings returns cached Settings instance."""
        os.environ["DATABASE_URL"] = "postgresql://localhost/test"

        settings1 = get_settings()
        settings2 = get_settings()

        assert settings1 is settings2

        # Cleanup
        del os.environ["DATABASE_URL"]
        get_settings.cache_clear()
