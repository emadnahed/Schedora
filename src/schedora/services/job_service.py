"""Job service for business logic."""
from uuid import UUID
from typing import Optional
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from schedora.repositories.job_repository import JobRepository
from schedora.services.state_machine import JobStateMachine
from schedora.api.schemas.job import JobCreate
from schedora.models.job import Job
from schedora.core.enums import JobStatus
from schedora.core.exceptions import (
    JobNotFoundError,
    DuplicateIdempotencyKeyError,
    InvalidStateTransitionError,
)


class JobService:
    """Service for job business logic and orchestration."""

    def __init__(self, db: Session, queue: Optional["RedisQueue"] = None):
        """
        Initialize service with database session.

        Args:
            db: SQLAlchemy database session
            queue: Optional RedisQueue for job distribution
        """
        self.db = db
        self.repository = JobRepository(db)
        self.queue = queue

    def create_job(self, job_data: JobCreate) -> Job:
        """
        Create a new job.

        Args:
            job_data: Job creation schema

        Returns:
            Job: Created job instance

        Raises:
            DuplicateIdempotencyKeyError: If idempotency key already exists
        """
        # Check for duplicate idempotency key
        existing_job = self.repository.get_by_idempotency_key(job_data.idempotency_key)
        if existing_job is not None:
            raise DuplicateIdempotencyKeyError(
                f"Job with idempotency key '{job_data.idempotency_key}' already exists"
            )

        try:
            job = self.repository.create(job_data.model_dump())
            self.db.commit()

            # Enqueue to Redis if status is PENDING and queue is available
            if self.queue and job.status == JobStatus.PENDING:
                self.queue.enqueue(job.job_id, priority=job.priority)

            return job
        except IntegrityError as e:
            # Handle race condition where duplicate was inserted between check and create
            if "idempotency_key" in str(e):
                raise DuplicateIdempotencyKeyError(
                    f"Job with idempotency key '{job_data.idempotency_key}' already exists"
                )
            raise

    def get_job(self, job_id: UUID) -> Job:
        """
        Get job by ID.

        Args:
            job_id: Job UUID

        Returns:
            Job: Job instance

        Raises:
            JobNotFoundError: If job not found
        """
        job = self.repository.get_by_id(job_id)
        if job is None:
            raise JobNotFoundError(f"Job {job_id} not found")
        return job

    def cancel_job(self, job_id: UUID) -> Job:
        """
        Cancel a job.

        Args:
            job_id: Job UUID

        Returns:
            Job: Updated job instance

        Raises:
            JobNotFoundError: If job not found
            InvalidStateTransitionError: If job is in terminal state
        """
        job = self.get_job(job_id)

        # Validate state transition
        JobStateMachine.validate_transition(job.status, JobStatus.CANCELED)

        # Update status
        updated_job = self.repository.update_status(job_id, JobStatus.CANCELED)

        # Remove from queue if present
        if self.queue:
            self.queue.remove(job_id)

        return updated_job

    def transition_status(self, job_id: UUID, new_status: JobStatus) -> Job:
        """
        Transition job to new status with validation.

        Args:
            job_id: Job UUID
            new_status: Target status

        Returns:
            Job: Updated job instance

        Raises:
            JobNotFoundError: If job not found
            InvalidStateTransitionError: If transition is invalid
        """
        job = self.get_job(job_id)

        # Validate state transition
        JobStateMachine.validate_transition(job.status, new_status)

        # Update status
        updated_job = self.repository.update_status(job_id, new_status)

        # Enqueue if transitioning to PENDING
        if self.queue and new_status == JobStatus.PENDING:
            self.queue.enqueue(job_id, priority=updated_job.priority)

        return updated_job
