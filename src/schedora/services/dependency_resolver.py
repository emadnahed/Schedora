"""Dependency resolution service for DAG workflows."""
from typing import List
from sqlalchemy.orm import Session
from schedora.models.job import Job
from schedora.core.enums import JobStatus


class DependencyResolver:
    """Service for resolving job dependencies in DAG workflows."""

    def __init__(self, db: Session):
        """
        Initialize dependency resolver.

        Args:
            db: SQLAlchemy database session
        """
        self.db = db

    def are_dependencies_met(self, job: Job) -> bool:
        """
        Check if all dependencies of a job are met (successfully completed).

        Args:
            job: Job instance to check

        Returns:
            bool: True if all dependencies are SUCCESS, False otherwise
        """
        # If no dependencies, job is ready
        if not job.dependencies:
            return True

        # All dependencies must be in SUCCESS state
        return all(dep.status == JobStatus.SUCCESS for dep in job.dependencies)

    def has_failed_dependencies(self, job: Job) -> bool:
        """
        Check if any dependencies have failed.

        Args:
            job: Job instance to check

        Returns:
            bool: True if any dependency is in FAILED or DEAD state
        """
        failed_states = {JobStatus.FAILED, JobStatus.DEAD, JobStatus.CANCELED}
        return any(dep.status in failed_states for dep in job.dependencies)

    def get_ready_jobs(self, limit: int = 100) -> List[Job]:
        """
        Get jobs that are ready to execute (dependencies met, status PENDING).

        Args:
            limit: Maximum number of jobs to return

        Returns:
            List[Job]: Jobs ready for execution
        """
        # Get pending jobs
        pending_jobs = (
            self.db.query(Job)
            .filter(Job.status == JobStatus.PENDING)
            .limit(limit)
            .all()
        )

        # Filter to only those with met dependencies
        ready_jobs = [
            job for job in pending_jobs
            if self.are_dependencies_met(job)
        ]

        return ready_jobs

    def get_blocked_jobs(self) -> List[Job]:
        """
        Get jobs that are blocked due to failed dependencies.

        Returns:
            List[Job]: Jobs that cannot proceed due to failed dependencies
        """
        pending_jobs = (
            self.db.query(Job)
            .filter(Job.status == JobStatus.PENDING)
            .all()
        )

        blocked_jobs = [
            job for job in pending_jobs
            if self.has_failed_dependencies(job)
        ]

        return blocked_jobs
