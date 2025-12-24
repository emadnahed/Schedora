"""Integration tests for AsyncWorker with Redis queue."""
import pytest
import asyncio
from uuid import uuid4
from schedora.worker.async_worker import AsyncWorker
from schedora.worker.handler_registry import HandlerRegistry
from schedora.services.redis_queue import RedisQueue
from schedora.services.job_service import JobService
from schedora.api.schemas.job import JobCreate
from schedora.core.enums import JobStatus


@pytest.mark.asyncio
@pytest.mark.integration
class TestAsyncWorkerWithQueue:
    """Test AsyncWorker integrates with Redis queue."""

    async def test_worker_dequeues_from_redis(self, db_session, redis_client):
        """Test worker dequeues jobs from Redis queue."""
        from schedora.worker.handlers.echo_handler import echo_handler

        queue = RedisQueue(redis_client, queue_name="test_worker_dequeue")
        queue.purge()

        registry = HandlerRegistry()
        registry.register_handler("echo", echo_handler)

        worker = AsyncWorker(
            worker_id="test-dequeue-worker",
            db_session=db_session,
            handler_registry=registry,
            max_concurrent_jobs=5,
            poll_interval=0.1,
            use_test_session=True,
            queue=queue,
        )

        # Create job using job service (auto-enqueues)
        job_service = JobService(db_session, queue=queue)
        job_data = JobCreate(
            type="echo",
            payload={"message": "test"},
            idempotency_key=f"test-{uuid4()}",
        )
        job = job_service.create_job(job_data)

        # Verify job is in queue
        assert queue.get_queue_length() == 1

        # Start worker
        worker_task = asyncio.create_task(worker.start())
        await asyncio.sleep(0.5)  # Let worker process job

        # Stop worker
        await worker.stop(timeout=2.0)
        try:
            await asyncio.wait_for(worker_task, timeout=1.0)
        except asyncio.TimeoutError:
            pass

        # Verify job was processed
        db_session.refresh(job)
        assert job.status == JobStatus.SUCCESS
        assert queue.get_queue_length() == 0

    async def test_worker_respects_priority(self, db_session, redis_client):
        """Test worker processes high priority jobs first."""
        from schedora.worker.handlers.echo_handler import echo_handler

        queue = RedisQueue(redis_client, queue_name="test_priority_worker")
        queue.purge()

        registry = HandlerRegistry()
        registry.register_handler("echo", echo_handler)

        worker = AsyncWorker(
            worker_id="test-priority-worker",
            db_session=db_session,
            handler_registry=registry,
            max_concurrent_jobs=1,  # Process one at a time
            poll_interval=0.1,
            use_test_session=True,
            queue=queue,
        )

        # Create low priority job
        job_service = JobService(db_session, queue=queue)
        low_priority_job = job_service.create_job(
            JobCreate(
                type="echo",
                payload={"message": "low"},
                idempotency_key=f"low-{uuid4()}",
                priority=1,
            )
        )

        # Create high priority job
        high_priority_job = job_service.create_job(
            JobCreate(
                type="echo",
                payload={"message": "high"},
                idempotency_key=f"high-{uuid4()}",
                priority=10,
            )
        )

        # High priority should be processed first
        assert queue.peek() == high_priority_job.job_id

        # Start worker
        worker_task = asyncio.create_task(worker.start())
        await asyncio.sleep(0.3)  # Process first job

        # Stop worker before second job
        await worker.stop(timeout=2.0)
        try:
            await asyncio.wait_for(worker_task, timeout=1.0)
        except asyncio.TimeoutError:
            pass

        # High priority should be done first
        db_session.refresh(high_priority_job)
        assert high_priority_job.status == JobStatus.SUCCESS

    async def test_worker_handles_empty_queue(self, db_session, redis_client):
        """Test worker handles empty queue gracefully."""
        from schedora.worker.handlers.echo_handler import echo_handler

        queue = RedisQueue(redis_client, queue_name="test_empty_queue")
        queue.purge()

        registry = HandlerRegistry()
        registry.register_handler("echo", echo_handler)

        worker = AsyncWorker(
            worker_id="test-empty-queue-worker",
            db_session=db_session,
            handler_registry=registry,
            max_concurrent_jobs=5,
            poll_interval=0.1,
            use_test_session=True,
            queue=queue,
        )

        # Start worker with empty queue
        worker_task = asyncio.create_task(worker.start())
        await asyncio.sleep(0.3)  # Worker polls empty queue

        # Worker should still be running
        assert worker.is_running

        # Stop worker
        await worker.stop(timeout=2.0)
        try:
            await asyncio.wait_for(worker_task, timeout=1.0)
        except asyncio.TimeoutError:
            pass

        assert not worker.is_running

    async def test_multiple_workers_dont_duplicate(self, db_session, redis_client):
        """Test multiple workers don't process same job."""
        from schedora.worker.handlers.sleep_handler import sleep_handler

        queue = RedisQueue(redis_client, queue_name="test_multi_worker")
        queue.purge()

        registry = HandlerRegistry()
        registry.register_handler("sleep", sleep_handler)

        # Create two workers
        worker1 = AsyncWorker(
            worker_id="test-multi-worker-1",
            db_session=db_session,
            handler_registry=registry,
            max_concurrent_jobs=5,
            poll_interval=0.1,
            use_test_session=True,
            queue=queue,
        )

        worker2 = AsyncWorker(
            worker_id="test-multi-worker-2",
            db_session=db_session,
            handler_registry=registry,
            max_concurrent_jobs=5,
            poll_interval=0.1,
            use_test_session=True,
            queue=queue,
        )

        # Create one job
        job_service = JobService(db_session, queue=queue)
        job = job_service.create_job(
            JobCreate(
                type="sleep",
                payload={"duration": 0.5},
                idempotency_key=f"sleep-{uuid4()}",
            )
        )

        # Start both workers
        task1 = asyncio.create_task(worker1.start())
        task2 = asyncio.create_task(worker2.start())
        await asyncio.sleep(1.0)  # Let workers process

        # Stop workers
        await worker1.stop(timeout=2.0)
        await worker2.stop(timeout=2.0)

        try:
            await asyncio.wait_for(asyncio.gather(task1, task2), timeout=2.0)
        except asyncio.TimeoutError:
            pass

        # Job should be processed exactly once
        db_session.refresh(job)
        assert job.status == JobStatus.SUCCESS
        # Only one worker should have processed it
        assert job.worker_id in ["test-multi-worker-1", "test-multi-worker-2"]

    async def test_worker_processes_multiple_jobs(self, db_session, redis_client):
        """Test worker processes multiple jobs from queue."""
        from schedora.worker.handlers.echo_handler import echo_handler

        queue = RedisQueue(redis_client, queue_name="test_multi_jobs")
        queue.purge()

        registry = HandlerRegistry()
        registry.register_handler("echo", echo_handler)

        worker = AsyncWorker(
            worker_id="test-multi-jobs-worker",
            db_session=db_session,
            handler_registry=registry,
            max_concurrent_jobs=10,
            poll_interval=0.1,
            use_test_session=True,
            queue=queue,
        )

        # Create 5 jobs
        job_service = JobService(db_session, queue=queue)
        jobs = []
        for i in range(5):
            job = job_service.create_job(
                JobCreate(
                    type="echo",
                    payload={"index": i},
                    idempotency_key=f"test-{uuid4()}",
                )
            )
            jobs.append(job)

        assert queue.get_queue_length() == 5

        # Start worker
        worker_task = asyncio.create_task(worker.start())
        await asyncio.sleep(1.0)  # Let worker process all jobs

        # Stop worker
        await worker.stop(timeout=2.0)
        try:
            await asyncio.wait_for(worker_task, timeout=1.0)
        except asyncio.TimeoutError:
            pass

        # All jobs should be processed
        for job in jobs:
            db_session.refresh(job)
            assert job.status == JobStatus.SUCCESS

        assert queue.get_queue_length() == 0

    async def test_worker_without_queue_still_works(self, db_session):
        """Test worker works without queue (backward compatibility)."""
        from schedora.worker.handlers.echo_handler import echo_handler
        from schedora.models.job import Job

        registry = HandlerRegistry()
        registry.register_handler("echo", echo_handler)

        worker = AsyncWorker(
            worker_id="test-no-queue-worker",
            db_session=db_session,
            handler_registry=registry,
            max_concurrent_jobs=5,
            poll_interval=0.1,
            use_test_session=True,
            # No queue parameter - uses DB polling
        )

        # Create job directly in DB
        job = Job(
            job_id=uuid4(),
            type="echo",
            payload={"message": "test"},
            idempotency_key=f"test-{uuid4()}",
            status=JobStatus.PENDING,
        )
        db_session.add(job)
        db_session.commit()

        # Start worker
        worker_task = asyncio.create_task(worker.start())
        await asyncio.sleep(0.5)  # Let worker process

        # Stop worker
        await worker.stop(timeout=2.0)
        try:
            await asyncio.wait_for(worker_task, timeout=1.0)
        except asyncio.TimeoutError:
            pass

        # Job should be processed
        db_session.refresh(job)
        assert job.status == JobStatus.SUCCESS
