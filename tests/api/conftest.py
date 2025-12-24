"""Fixtures for API tests."""
import pytest
from fastapi.testclient import TestClient
from schedora.main import app
from schedora.api.deps import get_db, get_redis_client


@pytest.fixture
def client(db_session, redis_client):
    """
    Create FastAPI test client with database and Redis overrides.

    Args:
        db_session: Test database session from root conftest
        redis_client: Test Redis client from root conftest

    Returns:
        TestClient: FastAPI test client
    """
    # Override get_db dependency
    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    # Override get_redis_client dependency
    def override_get_redis_client():
        return redis_client

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_redis_client] = override_get_redis_client

    with TestClient(app) as test_client:
        yield test_client

    app.dependency_overrides.clear()
