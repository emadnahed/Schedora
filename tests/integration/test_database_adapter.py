"""Integration tests for Database Adapter with actual database operations."""
import pytest
import asyncio
from datetime import datetime, timezone
from uuid import uuid4
from schedora.core.enums import JobStatus


@pytest.mark.integration
@pytest.mark.asyncio
class TestDatabaseAdapterIntegration:
    """Integration tests for DatabaseAdapter with actual DB operations."""

    async def test_asyncio_to_thread_works_with_db(self, db_session):
        """Test asyncio.to_thread can run sync DB operations."""
        from schedora.models.job import Job

        # Create test job in sync
        job = Job(
            job_id=uuid4(),
            type="test_job",
            payload={"test": "data"},
            idempotency_key=f"test-{uuid4()}",
            status=JobStatus.PENDING,
        )
        db_session.add(job)
        db_session.commit()

        # Query it using asyncio.to_thread
        async def query_job():
            return await asyncio.to_thread(
                lambda: db_session.query(Job).filter(Job.job_id == job.job_id).first()
            )

        result = await query_job()
        assert result is not None
        assert result.job_id == job.job_id

    async def test_asyncio_to_thread_doesnt_block_event_loop(self, db_session):
        """Test asyncio.to_thread allows concurrent operations."""
        from schedora.models.job import Job

        # Create multiple jobs
        jobs = []
        for i in range(3):
            job = Job(
                job_id=uuid4(),
                type="test_job",
                payload={"index": i},
                idempotency_key=f"test-concurrent-{i}",
                status=JobStatus.PENDING,
            )
            jobs.append(job)
            db_session.add(job)
        db_session.commit()

        # Query them concurrently using asyncio.to_thread
        async def query_job(job_id):
            await asyncio.sleep(0.01)  # Simulate some async work
            return await asyncio.to_thread(
                lambda: db_session.query(Job).filter(Job.job_id == job_id).first()
            )

        tasks = [query_job(j.job_id) for j in jobs]
        results = await asyncio.gather(*tasks)

        # Verify all jobs queried
        assert len(results) == 3
        for result in results:
            assert result is not None

    async def test_async_job_status_transition(self, db_session):
        """Test async job status transition using asyncio.to_thread."""
        from schedora.models.job import Job
        from schedora.services.job_service import JobService

        # Create test job
        job = Job(
            job_id=uuid4(),
            type="test_job",
            payload={"test": "data"},
            idempotency_key=f"test-{uuid4()}",
            status=JobStatus.RUNNING,
        )
        db_session.add(job)
        db_session.commit()

        # Transition status using asyncio.to_thread
        job_service = JobService(db_session)

        async def transition_status():
            return await asyncio.to_thread(
                job_service.transition_status,
                job.job_id,
                JobStatus.SUCCESS,
            )

        updated_job = await transition_status()
        assert updated_job.status == JobStatus.SUCCESS

    async def test_database_adapter_with_scheduler(self, db_session):
        """Test DatabaseAdapter can wrap Scheduler operations."""
        from schedora.worker.database_adapter import DatabaseAdapter
        from schedora.services.scheduler import Scheduler
        from schedora.models.job import Job

        # Create test job
        job = Job(
            job_id=uuid4(),
            type="test_job",
            payload={"test": "data"},
            idempotency_key=f"test-{uuid4()}",
            status=JobStatus.PENDING,
        )
        db_session.add(job)
        db_session.commit()

        # Use DatabaseAdapter to claim job async
        # Note: Scheduler needs worker_id in constructor
        async def claim_job_async(worker_id):
            scheduler = Scheduler(db_session, worker_id=worker_id)
            return await asyncio.to_thread(scheduler.claim_job)

        claimed_job = await claim_job_async("test-worker-1")

        assert claimed_job is not None
        assert claimed_job.status == JobStatus.SCHEDULED
        assert claimed_job.worker_id == "test-worker-1"
