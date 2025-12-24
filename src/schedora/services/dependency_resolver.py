"""Dependency resolution service for DAG workflows."""
from typing import List
from sqlalchemy.orm import Session
from sqlalchemy import select, exists
from schedora.models.job import Job, job_dependencies
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

        Uses optimized SQL query with subquery to filter at database level.

        Args:
            limit: Maximum number of jobs to return

        Returns:
            List[Job]: Jobs ready for execution
        """
        # Subquery to find jobs that have at least one unmet dependency
        # A dependency is unmet if it's not in SUCCESS state
        unmet_deps_subquery = (
            select(job_dependencies.c.job_id)
            .join(Job, Job.job_id == job_dependencies.c.depends_on_job_id)
            .where(Job.status != JobStatus.SUCCESS)
        )

        # Get PENDING jobs that either:
        # 1. Have no dependencies (not in job_dependencies table)
        # 2. All dependencies are SUCCESS (not in unmet_deps_subquery)
        ready_jobs = (
            self.db.query(Job)
            .filter(Job.status == JobStatus.PENDING)
            .filter(~Job.job_id.in_(unmet_deps_subquery))
            .limit(limit)
            .all()
        )

        return ready_jobs

    def get_blocked_jobs(self) -> List[Job]:
        """
        Get jobs that are blocked due to failed dependencies.

        Uses optimized SQL query with subquery to filter at database level.

        Returns:
            List[Job]: Jobs that cannot proceed due to failed dependencies
        """
        failed_states = {JobStatus.FAILED, JobStatus.DEAD, JobStatus.CANCELED}

        # Subquery to find jobs that have at least one failed dependency
        failed_deps_subquery = (
            select(job_dependencies.c.job_id)
            .join(Job, Job.job_id == job_dependencies.c.depends_on_job_id)
            .where(Job.status.in_(failed_states))
        )

        # Get PENDING jobs that have at least one failed dependency
        blocked_jobs = (
            self.db.query(Job)
            .filter(Job.status == JobStatus.PENDING)
            .filter(Job.job_id.in_(failed_deps_subquery))
            .all()
        )

        return blocked_jobs
