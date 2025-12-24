"""API tests for queue management endpoints."""
import pytest
from uuid import uuid4
from schedora.services.redis_queue import RedisQueue
from schedora.services.job_service import JobService
from schedora.api.schemas.job import JobCreate


@pytest.mark.api
class TestQueueAPI:
    """Test queue management API endpoints."""

    def test_get_queue_stats(self, client, db_session, redis_client):
        """Test GET /api/v1/queue/stats endpoint."""
        queue = RedisQueue(redis_client)
        queue.purge()
        queue.purge_dlq()

        # Create some jobs
        job_service = JobService(db_session, queue=queue)
        for i in range(5):
            job_service.create_job(
                JobCreate(
                    type="echo",
                    payload={"index": i},
                    idempotency_key=f"stats-test-{uuid4()}",
                )
            )

        # Move one to DLQ
        job = job_service.create_job(
            JobCreate(
                type="echo",
                payload={"test": "dlq"},
                idempotency_key=f"dlq-test-{uuid4()}",
            )
        )
        queue.move_to_dlq(job.job_id, "Test DLQ")

        response = client.get("/api/v1/queue/stats")

        assert response.status_code == 200
        data = response.json()
        assert data["pending_jobs"] == 5
        assert data["dlq_jobs"] == 1

    def test_purge_queue(self, client, db_session, redis_client):
        """Test POST /api/v1/queue/purge endpoint."""
        queue = RedisQueue(redis_client)
        queue.purge()

        # Create some jobs
        job_service = JobService(db_session, queue=queue)
        for i in range(10):
            job_service.create_job(
                JobCreate(
                    type="echo",
                    payload={"index": i},
                    idempotency_key=f"purge-test-{uuid4()}",
                )
            )

        assert queue.get_queue_length() == 10

        response = client.post("/api/v1/queue/purge")

        assert response.status_code == 200
        data = response.json()
        assert data["message"] == "Queue purged successfully"
        assert queue.get_queue_length() == 0

    def test_purge_dlq(self, client, db_session, redis_client):
        """Test POST /api/v1/queue/dlq/purge endpoint."""
        queue = RedisQueue(redis_client)
        queue.purge()
        queue.purge_dlq()

        # Create jobs and move to DLQ
        job_service = JobService(db_session, queue=queue)
        for i in range(5):
            job = job_service.create_job(
                JobCreate(
                    type="echo",
                    payload={"index": i},
                    idempotency_key=f"dlq-purge-test-{uuid4()}",
                )
            )
            queue.move_to_dlq(job.job_id, f"Test error {i}")

        assert queue.get_dlq_length() == 5

        response = client.post("/api/v1/queue/dlq/purge")

        assert response.status_code == 200
        data = response.json()
        assert data["message"] == "DLQ purged successfully"
        assert queue.get_dlq_length() == 0

    def test_peek_next_job(self, client, db_session, redis_client):
        """Test GET /api/v1/queue/peek endpoint."""
        queue = RedisQueue(redis_client)
        queue.purge()

        # Create jobs with different priorities
        job_service = JobService(db_session, queue=queue)
        low_priority = job_service.create_job(
            JobCreate(
                type="echo",
                payload={"priority": "low"},
                idempotency_key=f"low-{uuid4()}",
                priority=1,
            )
        )
        high_priority = job_service.create_job(
            JobCreate(
                type="echo",
                payload={"priority": "high"},
                idempotency_key=f"high-{uuid4()}",
                priority=10,
            )
        )

        response = client.get("/api/v1/queue/peek")

        assert response.status_code == 200
        data = response.json()
        # High priority should be next
        assert data["job_id"] == str(high_priority.job_id)

    def test_peek_empty_queue(self, client, redis_client):
        """Test peeking at empty queue."""
        queue = RedisQueue(redis_client)
        queue.purge()

        response = client.get("/api/v1/queue/peek")

        assert response.status_code == 404
        data = response.json()
        assert "No jobs in queue" in data["detail"]

    def test_get_queue_stats_no_redis(self, client):
        """Test queue stats when Redis is not configured (should handle gracefully)."""
        # This should work even without Redis (returns zeros or error)
        response = client.get("/api/v1/queue/stats")

        # Should either return 200 with zeros or appropriate error
        assert response.status_code in [200, 503]
