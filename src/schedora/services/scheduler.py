"""Scheduler service for atomic job claiming."""
import uuid
from typing import Optional, List
from datetime import datetime, timezone
from sqlalchemy.orm import Session
from sqlalchemy import and_, select
from schedora.models.job import Job, job_dependencies
from schedora.core.enums import JobStatus


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

    def claim_job(self) -> Optional[Job]:
        """
        Claim a single ready job atomically.

        Uses SELECT FOR UPDATE SKIP LOCKED for concurrent-safe claiming.
        Dependencies are checked in the SQL query before locking to minimize
        lock contention.

        Only claims jobs that are:
        - Status: PENDING
        - scheduled_at <= now
        - Dependencies met (if any)

        Returns:
            Job: Claimed job or None if no jobs available
        """
        now = datetime.now(timezone.utc)

        # Subquery to find jobs with unmet dependencies
        unmet_deps_subquery = (
            select(job_dependencies.c.job_id)
            .join(Job, Job.job_id == job_dependencies.c.depends_on_job_id)
            .where(Job.status != JobStatus.SUCCESS)
        )

        # Query for pending jobs that are ready to be scheduled
        # Include dependency check in the query to avoid locking jobs that aren't ready
        # Use FOR UPDATE SKIP LOCKED to prevent concurrent claims
        job = (
            self.db.query(Job)
            .filter(
                and_(
                    Job.status == JobStatus.PENDING,
                    Job.scheduled_at <= now,
                    ~Job.job_id.in_(unmet_deps_subquery)  # Only jobs with met dependencies
                )
            )
            .with_for_update(skip_locked=True)
            .first()
        )

        if not job:
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

        # Subquery to find jobs with unmet dependencies
        unmet_deps_subquery = (
            select(job_dependencies.c.job_id)
            .join(Job, Job.job_id == job_dependencies.c.depends_on_job_id)
            .where(Job.status != JobStatus.SUCCESS)
        )

        # Query for pending jobs with met dependencies
        candidate_jobs = (
            self.db.query(Job)
            .filter(
                and_(
                    Job.status == JobStatus.PENDING,
                    Job.scheduled_at <= now,
                    ~Job.job_id.in_(unmet_deps_subquery)  # Only jobs with met dependencies
                )
            )
            .with_for_update(skip_locked=True)
            .limit(limit)
            .all()
        )

        # Claim all candidate jobs
        claimed_jobs = []
        for job in candidate_jobs:
            job.status = JobStatus.SCHEDULED
            job.worker_id = self.worker_id
            claimed_jobs.append(job)

        if claimed_jobs:
            self.db.commit()

        return claimed_jobs
