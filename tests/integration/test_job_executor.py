"""Integration tests for Job Executor."""
import pytest
import asyncio
from datetime import datetime, timezone
from uuid import uuid4
from schedora.core.enums import JobStatus


@pytest.mark.integration
@pytest.mark.asyncio
class TestJobExecutor:
    """Integration tests for JobExecutor."""

    async def test_execute_job_successfully(self, db_session):
        """Test successful job execution (RUNNING → SUCCESS)."""
        from schedora.worker.job_executor import JobExecutor
        from schedora.worker.handler_registry import HandlerRegistry
        from schedora.worker.handlers.echo_handler import echo_handler
        from schedora.worker.database_adapter import DatabaseAdapter
        from schedora.services.job_service import JobService
        from schedora.models.job import Job

        # Create test job
        job = Job(
            job_id=uuid4(),
            type="echo",
            payload={"message": "test"},
            idempotency_key=f"test-{uuid4()}",
            status=JobStatus.RUNNING,
        )
        db_session.add(job)
        db_session.commit()

        # Setup handler registry
        registry = HandlerRegistry()
        registry.register_handler("echo", echo_handler)

        # Setup services
        job_service = JobService(db_session)
        adapter = DatabaseAdapter(job_service=job_service)

        # Execute job
        executor = JobExecutor(registry, adapter, job_service, use_test_session=True)
        result = await executor.execute(job)

        assert result.success is True
        assert result.result == {"message": "test"}

        # Verify job updated
        db_session.refresh(job)
        assert job.status == JobStatus.SUCCESS
        assert job.result == {"message": "test"}
        assert job.completed_at is not None

    async def test_execute_job_with_timeout(self, db_session):
        """Test job execution timeout."""
        from schedora.worker.job_executor import JobExecutor
        from schedora.worker.handler_registry import HandlerRegistry
        from schedora.worker.handlers.sleep_handler import sleep_handler
        from schedora.worker.database_adapter import DatabaseAdapter
        from schedora.services.job_service import JobService
        from schedora.models.job import Job

        # Create test job with short timeout
        job = Job(
            job_id=uuid4(),
            type="sleep",
            payload={"duration": 10},  # Sleep for 10 seconds
            idempotency_key=f"test-{uuid4()}",
            status=JobStatus.RUNNING,
            timeout_seconds=1,  # But timeout after 1 second
        )
        db_session.add(job)
        db_session.commit()

        # Setup handler registry
        registry = HandlerRegistry()
        registry.register_handler("sleep", sleep_handler)

        # Setup services
        job_service = JobService(db_session)
        adapter = DatabaseAdapter(job_service=job_service)

        # Execute job (should timeout)
        executor = JobExecutor(registry, adapter, job_service, use_test_session=True)
        result = await executor.execute(job)

        assert result.success is False
        assert "timeout" in result.error_message.lower() or "timed out" in result.error_message.lower()

    async def test_execute_job_with_handler_exception(self, db_session):
        """Test job execution with handler exception (RUNNING → FAILED)."""
        from schedora.worker.job_executor import JobExecutor
        from schedora.worker.handler_registry import HandlerRegistry
        from schedora.worker.handlers.fail_handler import fail_handler
        from schedora.worker.database_adapter import DatabaseAdapter
        from schedora.services.job_service import JobService
        from schedora.models.job import Job

        # Create test job
        job = Job(
            job_id=uuid4(),
            type="fail",
            payload={"error_message": "Test error"},
            idempotency_key=f"test-{uuid4()}",
            status=JobStatus.RUNNING,
            max_retries=0,  # No retries
        )
        db_session.add(job)
        db_session.commit()

        # Setup handler registry
        registry = HandlerRegistry()
        registry.register_handler("fail", fail_handler)

        # Setup services
        job_service = JobService(db_session)
        adapter = DatabaseAdapter(job_service=job_service)

        # Execute job (should fail)
        executor = JobExecutor(registry, adapter, job_service, use_test_session=True)
        result = await executor.execute(job)

        assert result.success is False
        assert "Test error" in result.error_message

        # Verify job marked as failed
        db_session.refresh(job)
        assert job.status == JobStatus.FAILED
        assert job.error_message is not None

    async def test_execute_job_updates_timestamps(self, db_session):
        """Test job execution updates started_at and completed_at."""
        from schedora.worker.job_executor import JobExecutor
        from schedora.worker.handler_registry import HandlerRegistry
        from schedora.worker.handlers.echo_handler import echo_handler
        from schedora.worker.database_adapter import DatabaseAdapter
        from schedora.services.job_service import JobService
        from schedora.models.job import Job

        # Create test job
        job = Job(
            job_id=uuid4(),
            type="echo",
            payload={"test": "data"},
            idempotency_key=f"test-{uuid4()}",
            status=JobStatus.RUNNING,
        )
        db_session.add(job)
        db_session.commit()

        assert job.started_at is None
        assert job.completed_at is None

        # Setup handler registry
        registry = HandlerRegistry()
        registry.register_handler("echo", echo_handler)

        # Setup services
        job_service = JobService(db_session)
        adapter = DatabaseAdapter(job_service=job_service)

        # Execute job
        executor = JobExecutor(registry, adapter, job_service, use_test_session=True)
        await executor.execute(job)

        # Verify timestamps updated
        db_session.refresh(job)
        assert job.started_at is not None
        assert job.completed_at is not None
        assert job.completed_at >= job.started_at

    async def test_execute_saves_result_to_database(self, db_session):
        """Test job execution saves result to database."""
        from schedora.worker.job_executor import JobExecutor
        from schedora.worker.handler_registry import HandlerRegistry
        from schedora.worker.database_adapter import DatabaseAdapter
        from schedora.services.job_service import JobService
        from schedora.models.job import Job

        async def custom_handler(payload):
            return {"computed": payload["value"] * 2, "status": "ok"}

        # Create test job
        job = Job(
            job_id=uuid4(),
            type="custom",
            payload={"value": 21},
            idempotency_key=f"test-{uuid4()}",
            status=JobStatus.RUNNING,
        )
        db_session.add(job)
        db_session.commit()

        # Setup handler registry
        registry = HandlerRegistry()
        registry.register_handler("custom", custom_handler)

        # Setup services
        job_service = JobService(db_session)
        adapter = DatabaseAdapter(job_service=job_service)

        # Execute job
        executor = JobExecutor(registry, adapter, job_service, use_test_session=True)
        await executor.execute(job)

        # Verify result saved
        db_session.refresh(job)
        assert job.result == {"computed": 42, "status": "ok"}

    async def test_execute_handler_not_found(self, db_session):
        """Test execution fails when handler not found."""
        from schedora.worker.job_executor import JobExecutor
        from schedora.worker.handler_registry import HandlerRegistry
        from schedora.worker.database_adapter import DatabaseAdapter
        from schedora.services.job_service import JobService
        from schedora.models.job import Job

        # Create test job with unregistered type
        job = Job(
            job_id=uuid4(),
            type="nonexistent",
            payload={},
            idempotency_key=f"test-{uuid4()}",
            status=JobStatus.RUNNING,
        )
        db_session.add(job)
        db_session.commit()

        # Empty registry
        registry = HandlerRegistry()

        # Setup services
        job_service = JobService(db_session)
        adapter = DatabaseAdapter(job_service=job_service)

        # Execute job (should fail with handler not found)
        executor = JobExecutor(registry, adapter, job_service, use_test_session=True)
        result = await executor.execute(job)

        assert result.success is False
        assert "handler" in result.error_message.lower() or "not found" in result.error_message.lower()
