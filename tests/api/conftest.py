"""Fixtures for API tests."""
import pytest
from fastapi.testclient import TestClient
from schedora.main import app
from schedora.api.deps import get_db


@pytest.fixture
def client(db_session):
    """
    Create FastAPI test client with database override.

    Args:
        db_session: Test database session from root conftest

    Returns:
        TestClient: FastAPI test client
    """
    # Override get_db dependency
    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db

    with TestClient(app) as test_client:
        yield test_client

    app.dependency_overrides.clear()
