"""API tests for health check endpoint."""
from fastapi.testclient import TestClient


class TestHealthAPI:
    """Test health check endpoint."""

    def test_health_check_success(self, client: TestClient):
        """Test health check returns 200 with status."""
        response = client.get("/api/v1/health")

        assert response.status_code == 200
        json_response = response.json()

        assert json_response["code"] == "HEALTH_0001"
        assert json_response["httpStatus"] == "OK"

        data = json_response["data"]
        assert data["status"] == "healthy"
        assert "database" in data

    def test_health_check_db_connection(self, client: TestClient):
        """Test health check validates DB connection."""
        response = client.get("/api/v1/health")

        json_response = response.json()
        data = json_response["data"]
        assert data["database"] == "connected"
