"""Job service for business logic."""
from uuid import UUID
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

    def __init__(self, db: Session):
        """
        Initialize service with database session.

        Args:
            db: SQLAlchemy database session
        """
        self.db = db
        self.repository = JobRepository(db)

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
        return self.repository.update_status(job_id, JobStatus.CANCELED)

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
        return self.repository.update_status(job_id, new_status)
