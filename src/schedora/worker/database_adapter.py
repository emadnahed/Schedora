"""Database adapter for bridging async workers with sync SQLAlchemy operations."""
import asyncio
from typing import Optional, Dict, Any
from uuid import UUID
from schedora.models.job import Job
from schedora.core.enums import JobStatus


class DatabaseAdapter:
    """
    Adapter for running sync database operations from async context.

    Uses asyncio.to_thread() to execute sync SQLAlchemy operations
    without blocking the async event loop. This bridges async workers
    with existing sync services.
    """

    def __init__(
        self,
        scheduler=None,
        state_machine=None,
        job_service=None,
        retry_service=None,
    ):
        """
        Initialize database adapter with service dependencies.

        Args:
            scheduler: Scheduler service for job claiming
            state_machine: State machine for job transitions
            job_service: Job service for updates
            retry_service: Retry service for scheduling retries
        """
        self.scheduler = scheduler
        self.state_machine = state_machine
        self.job_service = job_service
        self.retry_service = retry_service

    async def claim_job(self, worker_id: str) -> Optional[Job]:
        """
        Claim a job for execution (async wrapper).

        Args:
            worker_id: Worker identifier

        Returns:
            Optional[Job]: Claimed job or None if no jobs available
        """
        return await asyncio.to_thread(
            self.scheduler.claim_job,
            worker_id=worker_id,
        )

    async def transition_job_status(
        self, job_id: UUID, new_status: JobStatus
    ) -> Job:
        """
        Transition job to new status (async wrapper).

        Args:
            job_id: Job identifier
            new_status: Target status

        Returns:
            Job: Updated job instance
        """
        return await asyncio.to_thread(
            self.state_machine.transition,
            job_id=job_id,
            new_status=new_status,
        )

    async def update_job_result(
        self, job_id: UUID, result: Dict[str, Any]
    ) -> None:
        """
        Update job result (async wrapper).

        Args:
            job_id: Job identifier
            result: Job execution result
        """
        await asyncio.to_thread(
            self.job_service.update_job_result,
            job_id=job_id,
            result=result,
        )

    async def update_job_error(
        self,
        job_id: UUID,
        error_message: str,
        details: Optional[Dict[str, Any]] = None,
    ) -> None:
        """
        Update job error information (async wrapper).

        Args:
            job_id: Job identifier
            error_message: Error message
            details: Optional error details
        """
        await asyncio.to_thread(
            self.job_service.update_job_error,
            job_id=job_id,
            error_message=error_message,
            error_details=details,
        )

    async def update_job_timestamps(
        self,
        job_id: UUID,
        started_at: Optional[Any] = None,
        completed_at: Optional[Any] = None,
    ) -> None:
        """
        Update job timestamps (async wrapper).

        Args:
            job_id: Job identifier
            started_at: Job start time
            completed_at: Job completion time
        """
        await asyncio.to_thread(
            self.job_service.update_job_timestamps,
            job_id=job_id,
            started_at=started_at,
            completed_at=completed_at,
        )

    async def schedule_retry(
        self, job_id: UUID, error_message: str
    ) -> None:
        """
        Schedule job for retry (async wrapper).

        Args:
            job_id: Job identifier
            error_message: Error that caused retry
        """
        await asyncio.to_thread(
            self.retry_service.schedule_retry,
            job_id=job_id,
            error_message=error_message,
        )
