"""Integration tests for Job Service with Redis queue."""
import pytest
from uuid import uuid4
from schedora.services.job_service import JobService
from schedora.services.redis_queue import RedisQueue
from schedora.api.schemas.job import JobCreate
from schedora.core.enums import JobStatus


@pytest.mark.integration
class TestJobServiceWithQueue:
    """Test JobService integrates with Redis queue."""

    def test_create_pending_job_enqueues_to_redis(self, db_session, redis_client):
        """Test creating PENDING job automatically enqueues to Redis."""
        queue = RedisQueue(redis_client, queue_name="test_create_pending")
        queue.purge()

        job_service = JobService(db_session, queue=queue)

        job_data = JobCreate(
            type="echo",
            payload={"message": "test"},
            idempotency_key=f"test-{uuid4()}",
            # No scheduled_at means immediate execution (PENDING status)
        )

        job = job_service.create_job(job_data)

        # Verify job was enqueued to Redis
        assert queue.get_queue_length() == 1
        assert queue.peek() == job.job_id

    def test_create_job_with_priority(self, db_session, redis_client):
        """Test creating job with priority enqueues correctly."""
        queue = RedisQueue(redis_client, queue_name="test_priority")
        queue.purge()

        job_service = JobService(db_session, queue=queue)

        # Create low priority job
        job1_data = JobCreate(
            type="echo",
            payload={"message": "low"},
            idempotency_key=f"test-{uuid4()}",
            priority=1,
        )
        job1 = job_service.create_job(job1_data)

        # Create high priority job
        job2_data = JobCreate(
            type="echo",
            payload={"message": "high"},
            idempotency_key=f"test-{uuid4()}",
            priority=10,
        )
        job2 = job_service.create_job(job2_data)

        # High priority should be dequeued first
        assert queue.dequeue() == job2.job_id
        assert queue.dequeue() == job1.job_id

    def test_create_scheduled_job_not_enqueued(self, db_session, redis_client):
        """Test creating SCHEDULED job does not enqueue to Redis."""
        from datetime import datetime, timezone, timedelta

        queue = RedisQueue(redis_client, queue_name="test_scheduled")
        queue.purge()

        job_service = JobService(db_session, queue=queue)

        job_data = JobCreate(
            type="echo",
            payload={"message": "scheduled"},
            idempotency_key=f"test-{uuid4()}",
            scheduled_at=datetime.now(timezone.utc) + timedelta(hours=1),
        )

        job = job_service.create_job(job_data)

        # Verify job was created with SCHEDULED status
        assert job.status == JobStatus.SCHEDULED

        # Should NOT be enqueued (will be enqueued later when scheduled_at is reached)
        assert queue.get_queue_length() == 0

    def test_cancel_job_removes_from_queue(self, db_session, redis_client):
        """Test canceling job removes it from Redis queue."""
        queue = RedisQueue(redis_client, queue_name="test_cancel")
        queue.purge()

        job_service = JobService(db_session, queue=queue)

        job_data = JobCreate(
            type="echo",
            payload={"message": "test"},
            idempotency_key=f"test-{uuid4()}",
        )

        job = job_service.create_job(job_data)
        assert queue.get_queue_length() == 1

        # Cancel the job
        canceled_job = job_service.cancel_job(job.job_id)

        assert canceled_job.status == JobStatus.CANCELED
        # Should be removed from queue
        assert queue.get_queue_length() == 0

    def test_create_multiple_jobs_all_enqueued(self, db_session, redis_client):
        """Test creating multiple jobs enqueues all of them."""
        queue = RedisQueue(redis_client, queue_name="test_multiple")
        queue.purge()

        job_service = JobService(db_session, queue=queue)

        job_ids = []
        for i in range(5):
            job_data = JobCreate(
                type="echo",
                payload={"index": i},
                idempotency_key=f"test-{uuid4()}",
                priority=i,
            )
            job = job_service.create_job(job_data)
            job_ids.append(job.job_id)

        # All 5 jobs should be in queue
        assert queue.get_queue_length() == 5

        # Should dequeue in priority order (highest first)
        assert queue.dequeue() == job_ids[4]  # priority 4
        assert queue.dequeue() == job_ids[3]  # priority 3

    def test_create_job_without_queue_still_works(self, db_session):
        """Test JobService works without queue (backward compatibility)."""
        job_service = JobService(db_session)  # No queue

        job_data = JobCreate(
            type="echo",
            payload={"message": "test"},
            idempotency_key=f"test-{uuid4()}",
        )

        # Should not raise error
        job = job_service.create_job(job_data)
        assert job.status == JobStatus.PENDING

    def test_duplicate_idempotency_key_not_enqueued_twice(self, db_session, redis_client):
        """Test duplicate idempotency key doesn't enqueue twice."""
        from schedora.core.exceptions import DuplicateIdempotencyKeyError

        queue = RedisQueue(redis_client, queue_name="test_duplicate")
        queue.purge()

        job_service = JobService(db_session, queue=queue)

        idempotency_key = f"test-{uuid4()}"
        job_data = JobCreate(
            type="echo",
            payload={"message": "test"},
            idempotency_key=idempotency_key,
        )

        # First creation succeeds
        job = job_service.create_job(job_data)
        assert queue.get_queue_length() == 1

        # Second creation fails
        with pytest.raises(DuplicateIdempotencyKeyError):
            job_service.create_job(job_data)

        # Queue should still have only 1 job
        assert queue.get_queue_length() == 1

    def test_transition_to_pending_enqueues_job(self, db_session, redis_client):
        """Test transitioning job to PENDING enqueues it."""
        from datetime import datetime, timezone, timedelta

        queue = RedisQueue(redis_client, queue_name="test_transition")
        queue.purge()

        job_service = JobService(db_session, queue=queue)

        # Create scheduled job (not enqueued)
        job_data = JobCreate(
            type="echo",
            payload={"message": "test"},
            idempotency_key=f"test-{uuid4()}",
            scheduled_at=datetime.now(timezone.utc) + timedelta(hours=1),
        )

        job = job_service.create_job(job_data)
        assert job.status == JobStatus.SCHEDULED
        assert queue.get_queue_length() == 0

        # Transition to PENDING (should enqueue)
        updated_job = job_service.transition_status(job.job_id, JobStatus.PENDING)

        assert updated_job.status == JobStatus.PENDING
        assert queue.get_queue_length() == 1
        assert queue.peek() == job.job_id
