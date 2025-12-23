"""API tests for health check endpoint."""
from fastapi.testclient import TestClient


class TestHealthAPI:
    """Test health check endpoint."""

    def test_health_check_success(self, client: TestClient):
        """Test health check returns 200 with status."""
        response = client.get("/api/v1/health")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert "database" in data

    def test_health_check_db_connection(self, client: TestClient):
        """Test health check validates DB connection."""
        response = client.get("/api/v1/health")

        data = response.json()
        assert data["database"] == "connected"
