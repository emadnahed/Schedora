"""Integration tests for HeartbeatService."""
import pytest
import asyncio
from datetime import datetime, timezone, timedelta
from uuid import uuid4
from schedora.core.enums import JobStatus, WorkerStatus


@pytest.mark.integration
class TestHeartbeatService:
    """Integration tests for HeartbeatService."""

    def test_register_worker(self, db_session, redis_client):
        """Test registering a worker creates DB record and Redis keys."""
        from schedora.services.heartbeat_service import HeartbeatService
        from schedora.repositories.worker_repository import WorkerRepository

        service = HeartbeatService(db_session, redis_client)
        repo = WorkerRepository(db_session)

        worker_id = "test-worker-1"
        hostname = "test-host"
        pid = 12345
        max_concurrent_jobs = 5

        # Register worker
        worker = service.register_worker(
            worker_id=worker_id,
            hostname=hostname,
            pid=pid,
            max_concurrent_jobs=max_concurrent_jobs,
        )

        # Verify DB record
        assert worker.worker_id == worker_id
        assert worker.hostname == hostname
        assert worker.pid == pid
        assert worker.max_concurrent_jobs == max_concurrent_jobs
        assert worker.status == WorkerStatus.ACTIVE

        # Verify Redis heartbeat key
        heartbeat_key = f"worker:{worker_id}:heartbeat"
        assert redis_client.exists(heartbeat_key) == 1
        ttl = redis_client.ttl(heartbeat_key)
        assert ttl > 0

    def test_send_heartbeat_updates_redis_and_db(self, db_session, redis_client):
        """Test sending heartbeat updates Redis TTL and DB timestamp."""
        from schedora.services.heartbeat_service import HeartbeatService

        service = HeartbeatService(db_session, redis_client)

        # Register worker
        worker_id = "test-worker-2"
        worker = service.register_worker(worker_id, "host", 123, 5)

        # Wait a bit
        import time
        time.sleep(0.1)

        # Send heartbeat
        service.send_heartbeat(worker_id)

        # Verify Redis TTL refreshed
        heartbeat_key = f"worker:{worker_id}:heartbeat"
        ttl = redis_client.ttl(heartbeat_key)
        assert ttl > 80  # Should be close to timeout value

        # Verify DB timestamp updated
        db_session.refresh(worker)
        assert worker.last_heartbeat_at is not None

    def test_detect_stale_workers(self, db_session, redis_client):
        """Test detecting stale workers based on Redis TTL expiration."""
        from schedora.services.heartbeat_service import HeartbeatService
        from schedora.repositories.worker_repository import WorkerRepository

        service = HeartbeatService(db_session, redis_client)
        repo = WorkerRepository(db_session)

        # Register worker
        worker_id = "test-worker-3"
        worker = service.register_worker(worker_id, "host", 123, 5)

        # Manually expire the Redis key to simulate stale worker
        heartbeat_key = f"worker:{worker_id}:heartbeat"
        redis_client.delete(heartbeat_key)

        # Detect stale workers
        stale_workers = service.detect_stale_workers()

        # Verify worker marked as stale
        assert len(stale_workers) == 1
        assert stale_workers[0].worker_id == worker_id
        db_session.refresh(worker)
        assert worker.status == WorkerStatus.STALE

    def test_assign_and_remove_job_from_worker(self, db_session, redis_client):
        """Test tracking job assignments in Redis."""
        from schedora.services.heartbeat_service import HeartbeatService

        service = HeartbeatService(db_session, redis_client)

        # Register worker
        worker_id = "test-worker-4"
        service.register_worker(worker_id, "host", 123, 5)

        job_id = uuid4()

        # Assign job
        service.assign_job_to_worker(worker_id, job_id)

        # Verify job in Redis set
        jobs_key = f"worker:{worker_id}:jobs"
        job_ids = redis_client.smembers(jobs_key)
        assert str(job_id) in job_ids

        # Remove job
        service.remove_job_from_worker(worker_id, job_id)

        # Verify job removed from Redis set
        job_ids = redis_client.smembers(jobs_key)
        assert str(job_id) not in job_ids

    def test_get_worker_jobs(self, db_session, redis_client):
        """Test getting current jobs for a worker."""
        from schedora.services.heartbeat_service import HeartbeatService

        service = HeartbeatService(db_session, redis_client)

        # Register worker
        worker_id = "test-worker-5"
        service.register_worker(worker_id, "host", 123, 5)

        # Assign multiple jobs
        job_ids = [uuid4(), uuid4(), uuid4()]
        for job_id in job_ids:
            service.assign_job_to_worker(worker_id, job_id)

        # Get worker jobs
        current_jobs = service.get_worker_jobs(worker_id)

        # Verify all jobs returned
        assert len(current_jobs) == 3
        for job_id in job_ids:
            assert job_id in current_jobs

    def test_deregister_worker(self, db_session, redis_client):
        """Test deregistering a worker cleans up Redis and marks as STOPPED."""
        from schedora.services.heartbeat_service import HeartbeatService

        service = HeartbeatService(db_session, redis_client)

        # Register worker
        worker_id = "test-worker-6"
        worker = service.register_worker(worker_id, "host", 123, 5)

        # Assign a job
        job_id = uuid4()
        service.assign_job_to_worker(worker_id, job_id)

        # Deregister worker
        service.deregister_worker(worker_id)

        # Verify Redis keys removed
        heartbeat_key = f"worker:{worker_id}:heartbeat"
        jobs_key = f"worker:{worker_id}:jobs"
        assert redis_client.exists(heartbeat_key) == 0
        assert redis_client.exists(jobs_key) == 0

        # Verify worker marked as STOPPED
        db_session.refresh(worker)
        assert worker.status == WorkerStatus.STOPPED
        assert worker.stopped_at is not None

    def test_handle_stale_worker_reassigns_jobs(self, db_session, redis_client):
        """Test handling stale worker reassigns its jobs to PENDING."""
        from schedora.services.heartbeat_service import HeartbeatService
        from schedora.models.job import Job

        service = HeartbeatService(db_session, redis_client)

        # Register worker
        worker_id = "test-worker-7"
        service.register_worker(worker_id, "host", 123, 5)

        # Create jobs assigned to worker
        jobs = []
        for i in range(3):
            job = Job(
                job_id=uuid4(),
                type="test",
                payload={"index": i},
                idempotency_key=f"test-{uuid4()}",
                status=JobStatus.RUNNING,
            )
            jobs.append(job)
            db_session.add(job)
            service.assign_job_to_worker(worker_id, job.job_id)
        db_session.commit()

        # Handle stale worker
        service.handle_stale_worker(worker_id)

        # Verify jobs reassigned to PENDING
        for job in jobs:
            db_session.refresh(job)
            assert job.status == JobStatus.PENDING

        # Verify Redis jobs cleared
        jobs_key = f"worker:{worker_id}:jobs"
        assert redis_client.exists(jobs_key) == 0

    def test_cleanup_old_workers(self, db_session, redis_client):
        """Test cleaning up old stopped workers."""
        from schedora.services.heartbeat_service import HeartbeatService
        from schedora.repositories.worker_repository import WorkerRepository

        service = HeartbeatService(db_session, redis_client)
        repo = WorkerRepository(db_session)

        # Create old stopped worker (stopped over an hour ago)
        old_worker = repo.create(
            worker_id="old-worker",
            hostname="host",
            pid=123,
            version="1.0.0",
            max_concurrent_jobs=5,
            status=WorkerStatus.STOPPED,
            stopped_at=datetime.now(timezone.utc) - timedelta(hours=2),
        )

        # Create recent stopped worker
        recent_worker = repo.create(
            worker_id="recent-worker",
            hostname="host",
            pid=456,
            version="1.0.0",
            max_concurrent_jobs=5,
            status=WorkerStatus.STOPPED,
            stopped_at=datetime.now(timezone.utc) - timedelta(minutes=5),
        )

        # Cleanup old workers
        deleted_count = service.cleanup_old_workers()

        # Verify old worker deleted
        assert deleted_count == 1
        assert repo.get_by_id("old-worker") is None

        # Verify recent worker still exists
        assert repo.get_by_id("recent-worker") is not None
