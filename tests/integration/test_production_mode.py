"""Integration tests for production mode execution paths."""
import pytest
import asyncio
from uuid import uuid4
from datetime import datetime, timezone
from schedora.core.enums import JobStatus
from schedora.models.job import Job
from schedora.worker.job_executor import JobExecutor
from schedora.worker.handler_registry import HandlerRegistry
from schedora.worker.handlers.echo_handler import echo_handler
from schedora.worker.handlers.fail_handler import fail_handler
from schedora.services.job_service import JobService
from schedora.core.database import SessionLocal
from schedora.worker.database_adapter import DatabaseAdapter


@pytest.mark.integration
@pytest.mark.asyncio
class TestJobExecutorProductionMode:
    """Test JobExecutor in production mode (use_test_session=False)."""

    async def test_executor_production_mode_success(self, test_engine):
        """Test job execution in production mode with fresh sessions."""
        # Create job in database
        session = SessionLocal()
        try:
            job = Job(
                job_id=uuid4(),
                type="echo",
                payload={"message": "production test"},
                idempotency_key=f"prod-test-{uuid4()}",
                status=JobStatus.SCHEDULED,
            )
            session.add(job)
            session.commit()
            job_id = job.job_id
        finally:
            session.close()

        # Setup executor in production mode
        session2 = SessionLocal()
        try:
            registry = HandlerRegistry()
            registry.register_handler("echo", echo_handler)
            job_service = JobService(session2)
            adapter = DatabaseAdapter(job_service=job_service)

            executor = JobExecutor(
                handler_registry=registry,
                database_adapter=adapter,
                job_service=job_service,
                use_test_session=False  # Production mode
            )

            # Get job and execute
            job = job_service.get_job(job_id)
            await executor.execute(job)

            # Verify in new session
            session3 = SessionLocal()
            try:
                completed_job = session3.query(Job).filter(Job.job_id == job_id).first()
                assert completed_job.status == JobStatus.SUCCESS
                assert completed_job.result == {"message": "production test"}
                assert completed_job.started_at is not None
                assert completed_job.completed_at is not None
            finally:
                session3.close()
        finally:
            session2.close()

    async def test_executor_production_mode_failure(self, test_engine):
        """Test job failure in production mode saves error correctly."""
        # Create job that will fail
        session = SessionLocal()
        try:
            job = Job(
                job_id=uuid4(),
                type="fail",
                payload={"error_message": "Test failure"},
                idempotency_key=f"prod-fail-{uuid4()}",
                status=JobStatus.SCHEDULED,
                max_retries=0,  # No retries
            )
            session.add(job)
            session.commit()
            job_id = job.job_id
        finally:
            session.close()

        # Setup executor
        session2 = SessionLocal()
        try:
            registry = HandlerRegistry()
            registry.register_handler("fail", fail_handler)
            job_service = JobService(session2)
            adapter = DatabaseAdapter(job_service=job_service)

            executor = JobExecutor(
                handler_registry=registry,
                database_adapter=adapter,
                job_service=job_service,
                use_test_session=False
            )

            # Execute failing job
            job = job_service.get_job(job_id)
            await executor.execute(job)

            # Verify error saved
            session3 = SessionLocal()
            try:
                failed_job = session3.query(Job).filter(Job.job_id == job_id).first()
                assert failed_job.status == JobStatus.FAILED
                assert failed_job.error_message is not None
                assert "Test failure" in failed_job.error_message
            finally:
                session3.close()
        finally:
            session2.close()

    async def test_executor_production_update_timestamps(self, test_engine):
        """Test timestamps are updated correctly in production mode."""
        # Create job
        session = SessionLocal()
        try:
            job = Job(
                job_id=uuid4(),
                type="echo",
                payload={"test": "timestamps"},
                idempotency_key=f"prod-time-{uuid4()}",
                status=JobStatus.SCHEDULED,
            )
            session.add(job)
            session.commit()
            job_id = job.job_id
        finally:
            session.close()

        # Execute
        session2 = SessionLocal()
        try:
            registry = HandlerRegistry()
            registry.register_handler("echo", echo_handler)
            job_service = JobService(session2)
            adapter = DatabaseAdapter(job_service=job_service)
            executor = JobExecutor(registry, adapter, job_service, use_test_session=False)

            job = job_service.get_job(job_id)
            await executor.execute(job)

            # Check timestamps
            session3 = SessionLocal()
            try:
                completed = session3.query(Job).filter(Job.job_id == job_id).first()
                assert completed.started_at is not None
                assert completed.completed_at is not None
                assert completed.started_at < completed.completed_at
            finally:
                session3.close()
        finally:
            session2.close()

    async def test_executor_production_transition_status(self, test_engine):
        """Test status transitions work in production mode."""
        # Create job in SCHEDULED state
        session = SessionLocal()
        try:
            job = Job(
                job_id=uuid4(),
                type="echo",
                payload={"test": "status"},
                idempotency_key=f"prod-status-{uuid4()}",
                status=JobStatus.SCHEDULED,
            )
            session.add(job)
            session.commit()
            job_id = job.job_id
        finally:
            session.close()

        # Execute
        session2 = SessionLocal()
        try:
            registry = HandlerRegistry()
            registry.register_handler("echo", echo_handler)
            job_service = JobService(session2)
            adapter = DatabaseAdapter(job_service=job_service)
            executor = JobExecutor(registry, adapter, job_service, use_test_session=False)

            job = job_service.get_job(job_id)

            # Should transition SCHEDULED -> RUNNING -> SUCCESS
            await executor.execute(job)

            # Verify final status
            session3 = SessionLocal()
            try:
                final_job = session3.query(Job).filter(Job.job_id == job_id).first()
                assert final_job.status == JobStatus.SUCCESS
            finally:
                session3.close()
        finally:
            session2.close()


@pytest.mark.integration
@pytest.mark.asyncio
class TestAsyncWorkerProductionMode:
    """Test AsyncWorker production mode paths."""

    async def test_worker_production_mode_job_execution(self, test_engine):
        """Test worker executes job in production mode."""
        from schedora.worker.async_worker import AsyncWorker

        # Create job
        session = SessionLocal()
        try:
            job = Job(
                job_id=uuid4(),
                type="echo",
                payload={"msg": "worker prod test"},
                idempotency_key=f"worker-prod-{uuid4()}",
                status=JobStatus.PENDING,
            )
            session.add(job)
            session.commit()
            job_id = job.job_id
        finally:
            session.close()

        # Run worker in production mode
        session2 = SessionLocal()
        try:
            registry = HandlerRegistry()
            registry.register_handler("echo", echo_handler)

            worker = AsyncWorker(
                worker_id="prod-worker",
                db_session=session2,
                handler_registry=registry,
                max_concurrent_jobs=5,
                poll_interval=0.1,
                use_test_session=False  # Production mode
            )

            # Start worker briefly
            worker_task = asyncio.create_task(worker.start())
            await asyncio.sleep(0.5)
            await worker.stop()
            await worker_task

            # Verify job completed
            session3 = SessionLocal()
            try:
                completed = session3.query(Job).filter(Job.job_id == job_id).first()
                assert completed.status == JobStatus.SUCCESS
            finally:
                session3.close()
        finally:
            session2.close()

    async def test_worker_production_stop_with_running_tasks(self, test_engine):
        """Test worker stop with timeout in production mode."""
        from schedora.worker.async_worker import AsyncWorker
        from schedora.worker.handlers.sleep_handler import sleep_handler

        # Create long-running job
        session = SessionLocal()
        try:
            job = Job(
                job_id=uuid4(),
                type="sleep",
                payload={"duration": 5},  # Long job
                idempotency_key=f"worker-stop-{uuid4()}",
                status=JobStatus.PENDING,
            )
            session.add(job)
            session.commit()
        finally:
            session.close()

        # Run worker
        session2 = SessionLocal()
        try:
            registry = HandlerRegistry()
            registry.register_handler("sleep", sleep_handler)

            worker = AsyncWorker(
                worker_id="stop-test-worker",
                db_session=session2,
                handler_registry=registry,
                max_concurrent_jobs=5,
                poll_interval=0.1,
                use_test_session=False
            )

            # Start and quickly stop with timeout
            worker_task = asyncio.create_task(worker.start())
            await asyncio.sleep(0.3)  # Let job start
            await worker.stop(timeout=0.2)  # Short timeout
            await worker_task

            # Worker should stop gracefully
            assert not worker.is_running
        finally:
            session2.close()

    async def test_worker_production_handles_errors(self, test_engine, caplog):
        """Test worker handles errors in production mode poll loop."""
        from schedora.worker.async_worker import AsyncWorker
        from unittest.mock import patch

        session = SessionLocal()
        try:
            registry = HandlerRegistry()
            worker = AsyncWorker(
                worker_id="error-worker",
                db_session=session,
                handler_registry=registry,
                max_concurrent_jobs=5,
                poll_interval=0.1,
                use_test_session=False
            )

            # Mock _claim_job to raise error once
            call_count = 0
            original_claim = worker._claim_job

            async def mock_claim():
                nonlocal call_count
                call_count += 1
                if call_count == 1:
                    raise Exception("Production mode error")
                return await original_claim()

            worker._claim_job = mock_claim

            # Run briefly
            worker_task = asyncio.create_task(worker.start())
            await asyncio.sleep(0.3)
            await worker.stop()
            await worker_task

            # Should have logged error
            assert "Error in poll loop" in caplog.text
        finally:
            session.close()
