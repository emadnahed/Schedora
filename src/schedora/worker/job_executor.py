"""Job executor for running job handlers with timeout and error handling."""
import asyncio
import traceback
from datetime import datetime, timezone
from typing import Optional
from schedora.models.job import Job
from schedora.core.enums import JobStatus
from schedora.core.database import SessionLocal
from schedora.worker.models import ExecutionResult
from schedora.worker.handler_registry import HandlerRegistry


class JobExecutor:
    """
    Executes jobs by invoking registered handlers.

    Handles timeouts, errors, and result/error persistence.
    """

    def __init__(
        self,
        handler_registry: HandlerRegistry,
        database_adapter,
        job_service,
        use_test_session: bool = False,
    ):
        """
        Initialize job executor.

        Args:
            handler_registry: Registry of job type → handler mappings
            database_adapter: Async database adapter for updates
            job_service: Job service for persistence operations
            use_test_session: If True, reuse job_service for all operations (testing only)
        """
        self.registry = handler_registry
        self.adapter = database_adapter
        self.job_service = job_service
        self.use_test_session = use_test_session

    async def execute(self, job: Job) -> ExecutionResult:
        """
        Execute a job using its registered handler.

        Args:
            job: Job to execute

        Returns:
            ExecutionResult: Result of execution
        """
        # Get fresh job data to avoid session issues
        job_id = job.job_id
        job_type = job.type
        payload = job.payload
        timeout_seconds = job.timeout_seconds
        current_status = job.status

        # Transition to RUNNING (from SCHEDULED) if not already running
        if current_status != JobStatus.RUNNING:
            await self._transition_status(job_id, JobStatus.RUNNING)

        # Record start time
        started_at = datetime.now(timezone.utc)
        await self._update_timestamps(job_id, started_at=started_at)

        try:
            # Get handler
            if not self.registry.has_handler(job_type):
                raise KeyError(f"No handler registered for job type: {job_type}")

            handler = self.registry.get_handler(job_type)

            # Execute with timeout if specified
            if timeout_seconds:
                result = await self._run_handler_with_timeout(
                    handler, payload, timeout_seconds
                )
            else:
                result = await handler(payload)

            # Handle success
            return await self._handle_success(job_id, result)

        except asyncio.TimeoutError:
            # Handle timeout
            return await self._handle_failure(
                job_id,
                f"Job execution timed out after {timeout_seconds} seconds",
                {"timeout": True, "timeout_seconds": timeout_seconds},
            )

        except Exception as e:
            # Handle other errors
            error_message = str(e)
            error_details = {
                "type": type(e).__name__,
                "traceback": traceback.format_exc(),
            }
            return await self._handle_failure(job_id, error_message, error_details)

    async def _run_handler_with_timeout(
        self, handler, payload, timeout_seconds
    ):
        """
        Run handler with timeout.

        Args:
            handler: Handler function
            payload: Job payload
            timeout_seconds: Timeout in seconds

        Returns:
            Handler result

        Raises:
            asyncio.TimeoutError: If execution exceeds timeout
        """
        return await asyncio.wait_for(
            handler(payload),
            timeout=timeout_seconds,
        )

    async def _handle_success(self, job_id, result) -> ExecutionResult:
        """
        Handle successful job execution.

        Args:
            job_id: Job identifier
            result: Handler result

        Returns:
            ExecutionResult: Success result
        """
        completed_at = datetime.now(timezone.utc)

        # Update job status and result via async adapter
        await self._update_timestamps(job_id, completed_at=completed_at)
        await self._save_result(job_id, result)
        await self._transition_status(job_id, JobStatus.SUCCESS)

        return ExecutionResult(
            success=True,
            result=result,
        )

    async def _handle_failure(
        self,
        job_id,
        error_message: str,
        error_details: Optional[dict] = None,
    ) -> ExecutionResult:
        """
        Handle failed job execution.

        Args:
            job_id: Job identifier
            error_message: Error message
            error_details: Optional error details

        Returns:
            ExecutionResult: Failure result
        """
        completed_at = datetime.now(timezone.utc)

        # Update timestamps
        await self._update_timestamps(job_id, completed_at=completed_at)

        # Save error
        await self._save_error(job_id, error_message, error_details)

        # Transition to FAILED
        await self._transition_status(job_id, JobStatus.FAILED)

        return ExecutionResult(
            success=False,
            error_message=error_message,
            error_details=error_details,
        )

    async def _update_timestamps(
        self,
        job_id,
        started_at=None,
        completed_at=None,
    ):
        """Update job timestamps."""
        if self.use_test_session:
            # For testing: call directly in same thread
            job = self.job_service.get_job(job_id)
            if started_at:
                job.started_at = started_at
            if completed_at:
                job.completed_at = completed_at
            self.job_service.db.commit()
        else:
            # Production: create fresh session for thread safety
            def update_sync():
                session = SessionLocal()
                try:
                    job = session.query(Job).filter(Job.job_id == job_id).first()
                    if job:
                        if started_at:
                            job.started_at = started_at
                        if completed_at:
                            job.completed_at = completed_at
                        session.commit()
                finally:
                    session.close()
            await asyncio.to_thread(update_sync)

    async def _save_result(self, job_id, result):
        """Save job result."""
        if self.use_test_session:
            # For testing: call directly in same thread
            job = self.job_service.get_job(job_id)
            job.result = result
            self.job_service.db.commit()
        else:
            # Production: create fresh session for thread safety
            def save_sync():
                session = SessionLocal()
                try:
                    job = session.query(Job).filter(Job.job_id == job_id).first()
                    if job:
                        job.result = result
                        session.commit()
                finally:
                    session.close()
            await asyncio.to_thread(save_sync)

    async def _save_error(self, job_id, error_message, error_details):
        """Save job error."""
        if self.use_test_session:
            # For testing: call directly in same thread
            job = self.job_service.get_job(job_id)
            job.error_message = error_message
            job.error_details = error_details
            self.job_service.db.commit()
        else:
            # Production: create fresh session for thread safety
            def save_sync():
                session = SessionLocal()
                try:
                    job = session.query(Job).filter(Job.job_id == job_id).first()
                    if job:
                        job.error_message = error_message
                        job.error_details = error_details
                        session.commit()
                finally:
                    session.close()
            await asyncio.to_thread(save_sync)

    async def _transition_status(self, job_id, new_status):
        """Transition job status."""
        if self.use_test_session:
            # For testing: call directly in same thread
            self.job_service.transition_status(job_id, new_status)
        else:
            # Production: create fresh session for thread safety
            def transition_sync():
                from schedora.services.state_machine import JobStateMachine
                session = SessionLocal()
                try:
                    job = session.query(Job).filter(Job.job_id == job_id).first()
                    if job:
                        # Validate and apply state transition
                        JobStateMachine.validate_transition(job.status, new_status)
                        job.status = new_status
                        session.commit()
                finally:
                    session.close()
            await asyncio.to_thread(transition_sync)
