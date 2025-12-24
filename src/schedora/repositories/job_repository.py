"""Job repository for database operations."""
from typing import Optional, Dict, Any
from uuid import UUID
from sqlalchemy.orm import Session
from schedora.models.job import Job
from schedora.core.enums import JobStatus
from schedora.core.exceptions import JobNotFoundError


class JobRepository:
    """Repository for Job database operations."""

    def __init__(self, db: Session):
        """
        Initialize repository with database session.

        Args:
            db: SQLAlchemy database session
        """
        self.db = db

    def create(self, job_data: Dict[str, Any]) -> Job:
        """
        Create a new job in the database.

        Args:
            job_data: Dictionary of job attributes

        Returns:
            Job: Created job instance
        """
        from datetime import datetime, timezone

        job = Job(**job_data)

        # Set status to SCHEDULED if scheduled_at is in the future
        if job.scheduled_at and job.scheduled_at > datetime.now(timezone.utc):
            job.status = JobStatus.SCHEDULED

        self.db.add(job)
        self.db.commit()
        self.db.refresh(job)
        return job

    def get_by_id(self, job_id: UUID) -> Optional[Job]:
        """
        Retrieve job by ID.

        Args:
            job_id: Job UUID

        Returns:
            Optional[Job]: Job instance or None if not found
        """
        return self.db.query(Job).filter(Job.job_id == job_id).first()

    def get_by_idempotency_key(self, idempotency_key: str) -> Optional[Job]:
        """
        Retrieve job by idempotency key.

        Args:
            idempotency_key: Unique idempotency key

        Returns:
            Optional[Job]: Job instance or None if not found
        """
        return (
            self.db.query(Job)
            .filter(Job.idempotency_key == idempotency_key)
            .first()
        )

    def update_status(self, job_id: UUID, status: JobStatus) -> Job:
        """
        Update job status.

        Args:
            job_id: Job UUID
            status: New job status

        Returns:
            Job: Updated job instance

        Raises:
            JobNotFoundError: If job not found
        """
        job = self.get_by_id(job_id)
        if job is None:
            raise JobNotFoundError(f"Job {job_id} not found")

        job.status = status
        self.db.commit()
        self.db.refresh(job)
        return job
