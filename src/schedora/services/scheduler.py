"""Scheduler service for atomic job claiming."""
import uuid
from typing import Optional, List
from datetime import datetime, timezone
from sqlalchemy.orm import Session
from sqlalchemy import and_
from schedora.models.job import Job
from schedora.core.enums import JobStatus
from schedora.services.dependency_resolver import DependencyResolver


class Scheduler:
    """Service for atomically claiming ready jobs."""

    def __init__(self, db: Session, worker_id: Optional[str] = None):
        """
        Initialize scheduler.

        Args:
            db: SQLAlchemy database session
            worker_id: Optional worker identifier, generates UUID if not provided
        """
        self.db = db
        self.worker_id = worker_id or f"worker-{uuid.uuid4()}"
        self.dependency_resolver = DependencyResolver(db)

    def claim_job(self) -> Optional[Job]:
        """
        Claim a single ready job atomically.

        Uses SELECT FOR UPDATE SKIP LOCKED for concurrent-safe claiming.
        Only claims jobs that are:
        - Status: PENDING
        - scheduled_at <= now
        - Dependencies met (if any)

        Returns:
            Job: Claimed job or None if no jobs available
        """
        now = datetime.now(timezone.utc)

        # Query for pending jobs that are ready to be scheduled
        # Use FOR UPDATE SKIP LOCKED to prevent concurrent claims
        job = (
            self.db.query(Job)
            .filter(
                and_(
                    Job.status == JobStatus.PENDING,
                    Job.scheduled_at <= now
                )
            )
            .with_for_update(skip_locked=True)
            .first()
        )

        if not job:
            return None

        # Check if dependencies are met
        if not self.dependency_resolver.are_dependencies_met(job):
            return None

        # Claim the job
        job.status = JobStatus.SCHEDULED
        job.worker_id = self.worker_id
        self.db.commit()

        return job

    def claim_ready_jobs(self, limit: int = 10) -> List[Job]:
        """
        Claim multiple ready jobs in batch.

        Args:
            limit: Maximum number of jobs to claim

        Returns:
            List[Job]: List of claimed jobs
        """
        now = datetime.now(timezone.utc)
        claimed_jobs = []

        # Query for pending jobs
        candidate_jobs = (
            self.db.query(Job)
            .filter(
                and_(
                    Job.status == JobStatus.PENDING,
                    Job.scheduled_at <= now
                )
            )
            .with_for_update(skip_locked=True)
            .limit(limit)
            .all()
        )

        for job in candidate_jobs:
            # Check dependencies for each job
            if self.dependency_resolver.are_dependencies_met(job):
                job.status = JobStatus.SCHEDULED
                job.worker_id = self.worker_id
                claimed_jobs.append(job)

        if claimed_jobs:
            self.db.commit()

        return claimed_jobs
