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
        assert "redis" in data
        assert "workers" in data

    def test_health_check_db_connection(self, client: TestClient):
        """Test health check validates DB connection."""
        response = client.get("/api/v1/health")

        json_response = response.json()
        data = json_response["data"]
        assert data["database"] == "connected"

    def test_health_check_redis_connection(self, client: TestClient):
        """Test health check includes Redis connection status."""
        response = client.get("/api/v1/health")

        json_response = response.json()
        data = json_response["data"]
        assert "redis" in data
        assert data["redis"] == "connected"

    def test_health_check_worker_statistics(self, client: TestClient, db_session):
        """Test health check includes worker statistics."""
        # Create some test workers
        from schedora.repositories.worker_repository import WorkerRepository
        from schedora.core.enums import WorkerStatus

        repo = WorkerRepository(db_session)

        # Create 2 active workers
        repo.create(
            worker_id="worker-1",
            hostname="host1",
            pid=1001,
            version="1.0.0",
            max_concurrent_jobs=5,
            status=WorkerStatus.ACTIVE,
        )
        repo.create(
            worker_id="worker-2",
            hostname="host2",
            pid=1002,
            version="1.0.0",
            max_concurrent_jobs=5,
            status=WorkerStatus.ACTIVE,
        )

        # Create 1 stale worker
        repo.create(
            worker_id="worker-3",
            hostname="host3",
            pid=1003,
            version="1.0.0",
            max_concurrent_jobs=5,
            status=WorkerStatus.STALE,
        )

        response = client.get("/api/v1/health")

        json_response = response.json()
        data = json_response["data"]

        assert "workers" in data
        workers = data["workers"]
        assert workers["total"] == 3
        assert workers["active"] == 2
        assert workers["stale"] == 1
