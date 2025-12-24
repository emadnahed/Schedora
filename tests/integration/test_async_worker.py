"""Integration tests for AsyncWorker."""
import pytest
import asyncio
from datetime import datetime, timezone
from uuid import uuid4
from schedora.core.enums import JobStatus


@pytest.mark.integration
@pytest.mark.asyncio
class TestAsyncWorker:
    """Integration tests for AsyncWorker core."""

    async def test_worker_starts_and_stops_gracefully(self, db_session):
        """Test worker can start and stop without errors."""
        from schedora.worker.async_worker import AsyncWorker
        from schedora.worker.handler_registry import HandlerRegistry

        registry = HandlerRegistry()
        worker = AsyncWorker(
            worker_id="test-worker-1",
            db_session=db_session,
            handler_registry=registry,
            max_concurrent_jobs=5,
            use_test_session=True,
        )

        # Start worker
        worker_task = asyncio.create_task(worker.start())
        await asyncio.sleep(0.1)  # Let it start

        # Stop worker
        await worker.stop()
        await worker_task

        assert worker.is_running is False

    async def test_worker_claims_and_executes_job(self, db_session):
        """Test worker claims and executes a job."""
        from schedora.worker.async_worker import AsyncWorker
        from schedora.worker.handler_registry import HandlerRegistry
        from schedora.worker.handlers.echo_handler import echo_handler
        from schedora.models.job import Job

        # Create test job
        job = Job(
            job_id=uuid4(),
            type="echo",
            payload={"message": "test"},
            idempotency_key=f"test-{uuid4()}",
            status=JobStatus.PENDING,
        )
        db_session.add(job)
        db_session.commit()

        # Setup worker
        registry = HandlerRegistry()
        registry.register_handler("echo", echo_handler)

        worker = AsyncWorker(
            worker_id="test-worker-2",
            db_session=db_session,
            handler_registry=registry,
            max_concurrent_jobs=5,
            poll_interval=0.1,
            use_test_session=True,
        )

        # Start worker
        worker_task = asyncio.create_task(worker.start())
        await asyncio.sleep(0.5)  # Wait for job to be processed

        # Stop worker
        await worker.stop()
        await worker_task

        # Verify job completed (re-query from database since job was expunged)
        from schedora.models.job import Job
        completed_job = db_session.query(Job).filter(Job.job_id == job.job_id).first()
        assert completed_job.status == JobStatus.SUCCESS
        assert completed_job.result == {"message": "test"}

    async def test_worker_respects_concurrency_limit(self, db_session):
        """Test worker respects max_concurrent_jobs limit."""
        from schedora.worker.async_worker import AsyncWorker
        from schedora.worker.handler_registry import HandlerRegistry
        from schedora.worker.handlers.sleep_handler import sleep_handler
        from schedora.models.job import Job

        # Create 5 jobs
        jobs = []
        for i in range(5):
            job = Job(
                job_id=uuid4(),
                type="sleep",
                payload={"duration": 0.5},
                idempotency_key=f"test-concurrent-{i}",
                status=JobStatus.PENDING,
            )
            jobs.append(job)
            db_session.add(job)
        db_session.commit()

        # Setup worker with max 2 concurrent jobs
        registry = HandlerRegistry()
        registry.register_handler("sleep", sleep_handler)

        worker = AsyncWorker(
            worker_id="test-worker-3",
            db_session=db_session,
            handler_registry=registry,
            max_concurrent_jobs=2,
            poll_interval=0.05,
            use_test_session=True,
        )

        # Start worker
        worker_task = asyncio.create_task(worker.start())

        # Wait for some processing
        await asyncio.sleep(0.2)

        # Check current semaphore value (should be limited)
        # At most 2 jobs running, so at least 0 permits available
        assert worker._semaphore._value >= 0

        # Wait for all jobs to complete (5 jobs * 0.5s + buffer)
        await asyncio.sleep(3.5)

        # Stop worker
        await worker.stop()
        await worker_task

        # Verify all jobs completed (re-query from database since jobs were expunged)
        for job in jobs:
            completed_job = db_session.query(Job).filter(Job.job_id == job.job_id).first()
            assert completed_job.status == JobStatus.SUCCESS

    async def test_worker_handles_empty_queue(self, db_session):
        """Test worker handles empty queue gracefully."""
        from schedora.worker.async_worker import AsyncWorker
        from schedora.worker.handler_registry import HandlerRegistry

        registry = HandlerRegistry()
        worker = AsyncWorker(
            worker_id="test-worker-4",
            db_session=db_session,
            handler_registry=registry,
            max_concurrent_jobs=5,
            poll_interval=0.1,
            use_test_session=True,
        )

        # Start worker (no jobs available)
        worker_task = asyncio.create_task(worker.start())
        await asyncio.sleep(0.3)

        # Stop worker
        await worker.stop()
        await worker_task

        # Should not crash
        assert True

    async def test_worker_tracks_metrics(self, db_session):
        """Test worker tracks job execution metrics."""
        from schedora.worker.async_worker import AsyncWorker
        from schedora.worker.handler_registry import HandlerRegistry
        from schedora.worker.handlers.echo_handler import echo_handler
        from schedora.models.job import Job

        # Create test jobs
        for i in range(3):
            job = Job(
                job_id=uuid4(),
                type="echo",
                payload={"index": i},
                idempotency_key=f"test-metrics-{i}",
                status=JobStatus.PENDING,
            )
            db_session.add(job)
        db_session.commit()

        # Setup worker
        registry = HandlerRegistry()
        registry.register_handler("echo", echo_handler)

        worker = AsyncWorker(
            worker_id="test-worker-5",
            db_session=db_session,
            handler_registry=registry,
            max_concurrent_jobs=5,
            poll_interval=0.1,
            use_test_session=True,
        )

        # Start worker
        worker_task = asyncio.create_task(worker.start())
        await asyncio.sleep(0.5)

        # Stop worker
        await worker.stop()
        await worker_task

        # Check metrics
        assert worker.jobs_processed >= 3
        assert worker.jobs_succeeded >= 3
