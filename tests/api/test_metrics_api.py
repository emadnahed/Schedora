"""API tests for Prometheus metrics endpoint."""
import pytest


@pytest.mark.api
class TestMetricsAPI:
    """Test metrics endpoint."""

    def test_metrics_endpoint_returns_prometheus_format(self, client):
        """Test /metrics endpoint returns Prometheus format."""
        response = client.get("/api/v1/metrics")

        assert response.status_code == 200
        assert "text/plain" in response.headers["content-type"]

        # Check for expected Prometheus metrics
        content = response.text
        assert "schedora_system_info" in content
        assert "schedora_workers_active" in content
        assert "schedora_workers_stale" in content

    def test_metrics_includes_http_request_metrics(self, client):
        """Test metrics include HTTP request tracking."""
        # Make some requests
        client.get("/api/v1/health")
        client.get("/api/v1/queue/stats")

        # Get metrics
        response = client.get("/api/v1/metrics")

        assert response.status_code == 200
        content = response.text

        # Should include HTTP metrics
        assert "schedora_http_requests_total" in content
        assert "schedora_http_request_duration_seconds" in content

    def test_metrics_includes_worker_stats(self, client, db_session):
        """Test metrics include worker statistics."""
        from schedora.repositories.worker_repository import WorkerRepository
        from schedora.core.enums import WorkerStatus

        repo = WorkerRepository(db_session)

        # Create some workers
        repo.create(
            worker_id="metrics-worker-1",
            hostname="host",
            pid=123,
            version="1.0.0",
            max_concurrent_jobs=5,
            status=WorkerStatus.ACTIVE,
        )

        repo.create(
            worker_id="metrics-worker-2",
            hostname="host",
            pid=124,
            version="1.0.0",
            max_concurrent_jobs=5,
            status=WorkerStatus.STALE,
        )

        # Get metrics
        response = client.get("/api/v1/metrics")

        assert response.status_code == 200
        content = response.text

        # Should show worker counts
        assert "schedora_workers_active 1" in content
        assert "schedora_workers_stale 1" in content

    def test_metrics_includes_queue_stats(self, client, db_session, redis_client):
        """Test metrics include queue statistics."""
        from schedora.services.redis_queue import RedisQueue
        from schedora.services.job_service import JobService
        from schedora.api.schemas.job import JobCreate
        from uuid import uuid4

        queue = RedisQueue(redis_client)
        queue.purge()

        # Create some jobs in queue
        job_service = JobService(db_session, queue=queue)
        for i in range(3):
            job_service.create_job(
                JobCreate(
                    type="echo",
                    payload={"index": i},
                    idempotency_key=f"metrics-test-{uuid4()}",
                )
            )

        # Get metrics
        response = client.get("/api/v1/metrics")

        assert response.status_code == 200
        content = response.text

        # Should show queue length
        assert "schedora_queue_length" in content
        assert 'queue_name="jobs"' in content
