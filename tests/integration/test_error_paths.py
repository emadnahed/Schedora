"""Integration tests for error paths and edge cases to achieve 100% coverage."""
import pytest
import asyncio
from unittest.mock import Mock, patch, MagicMock
from uuid import uuid4
from datetime import datetime, timezone
from schedora.core.enums import JobStatus, WorkerStatus
from schedora.models.job import Job
from schedora.models.worker import Worker
from schedora.worker.async_worker import AsyncWorker
from schedora.worker.handler_registry import HandlerRegistry
from schedora.worker.handlers.echo_handler import echo_handler
from schedora.repositories.worker_repository import WorkerRepository
from schedora.services.job_service import JobService
from schedora.services.workflow_service import WorkflowService
from schedora.services.retry_service import RetryService
from schedora.core.enums import RetryPolicy
from tests.factories.job_factory import create_job


@pytest.mark.integration
@pytest.mark.asyncio
class TestAsyncWorkerErrorPaths:
    """Test AsyncWorker error paths for coverage."""

    async def test_worker_stop_with_timeout(self, db_session):
        """Test worker stop with tasks that timeout."""
        from schedora.worker.handlers.sleep_handler import sleep_handler

        registry = HandlerRegistry()
        registry.register_handler("sleep", sleep_handler)

        worker = AsyncWorker(
            worker_id="timeout-test",
            db_session=db_session,
            handler_registry=registry,
            max_concurrent_jobs=5,
            use_test_session=True,
        )

        # Create long-running job
        job = Job(
            job_id=uuid4(),
            type="sleep",
            payload={"duration": 10},  # 10 seconds
            idempotency_key=f"timeout-{uuid4()}",
            status=JobStatus.PENDING,
        )
        db_session.add(job)
        db_session.commit()

        # Start worker and quickly stop with short timeout
        worker_task = asyncio.create_task(worker.start())
        await asyncio.sleep(0.2)  # Let job start

        # Stop with very short timeout to trigger TimeoutError path
        await worker.stop(timeout=0.01)

        try:
            await asyncio.wait_for(worker_task, timeout=1.0)
        except asyncio.TimeoutError:
            pass  # Expected

        assert not worker.is_running

    async def test_worker_claim_job_error_in_test_mode(self, db_session):
        """Test claim_job error handling in test mode."""
        registry = HandlerRegistry()

        # Mock scheduler to raise an exception
        mock_scheduler = Mock()
        mock_scheduler.claim_job.side_effect = Exception("Test claim error")

        worker = AsyncWorker(
            worker_id="claim-error-test",
            db_session=db_session,
            handler_registry=registry,
            max_concurrent_jobs=5,
            use_test_session=True,
        )
        worker.scheduler = mock_scheduler

        # Claim should return None on error
        job = await worker._claim_job()
        assert job is None

    async def test_worker_execution_unexpected_error(self, db_session):
        """Test unexpected error during job execution."""
        # Create handler that raises an unexpected error
        async def bad_handler(payload):
            raise RuntimeError("Unexpected error")

        registry = HandlerRegistry()
        registry.register_handler("bad", bad_handler)

        job = Job(
            job_id=uuid4(),
            type="bad",
            payload={},
            idempotency_key=f"bad-{uuid4()}",
            status=JobStatus.PENDING,
        )
        db_session.add(job)
        db_session.commit()

        worker = AsyncWorker(
            worker_id="unexpected-error-test",
            db_session=db_session,
            handler_registry=registry,
            max_concurrent_jobs=5,
            poll_interval=0.1,
            use_test_session=True,
        )

        # Execute job - should handle the unexpected error
        await worker._execute_job_with_semaphore(job)

        # Verify metrics tracked the failure
        assert worker.jobs_failed > 0


@pytest.mark.integration
class TestRetryServiceEdgeCases:
    """Test RetryService edge cases."""

    def test_jitter_policy_with_zero_retry_count(self, db_session):
        """Test jitter policy with retry_count=0 (covers line 49)."""
        from schedora.services.retry_service import RetryService

        retry_service = RetryService()

        # Test with retry_count=0 to cover the jitter randomization path
        next_retry = retry_service.calculate_next_retry(
            retry_count=0,
            max_retries=3,
            retry_policy=RetryPolicy.JITTER
        )

        # Should return a valid datetime in the future
        assert next_retry > datetime.now(timezone.utc)


@pytest.mark.integration
class TestWorkerRepositoryEdgeCases:
    """Test WorkerRepository edge cases."""

    def test_increment_jobs_not_found(self, db_session):
        """Test incrementing job count for nonexistent worker."""
        repo = WorkerRepository(db_session)

        with pytest.raises(ValueError, match="Worker .* not found"):
            repo.increment_current_jobs("nonexistent-worker")

    def test_decrement_jobs_not_found(self, db_session):
        """Test decrementing job count for nonexistent worker."""
        repo = WorkerRepository(db_session)

        with pytest.raises(ValueError, match="Worker .* not found"):
            repo.decrement_current_jobs("nonexistent-worker")

    def test_delete_old_workers_none_to_delete(self, db_session):
        """Test deleting old workers when none exist."""
        repo = WorkerRepository(db_session)

        # No old workers to delete
        deleted = repo.delete_old_stopped_workers(cleanup_after_seconds=3600)
        assert deleted == 0


@pytest.mark.integration
class TestWorkflowServiceErrorPaths:
    """Test WorkflowService error paths."""

    def test_get_workflow_status_empty_workflow(self, db_session):
        """Test getting workflow status when workflow has no jobs (covers line 120)."""
        from schedora.repositories.workflow_repository import WorkflowRepository
        from schedora.core.enums import WorkflowStatus

        workflow_repo = WorkflowRepository(db_session)
        workflow = workflow_repo.create(name="empty-workflow")

        workflow_service = WorkflowService(db_session)
        status = workflow_service.get_workflow_status(workflow.workflow_id)

        # When total_jobs = 0, status should be PENDING (line 124)
        assert status["total_jobs"] == 0
        assert status["status"] == str(WorkflowStatus.PENDING)
