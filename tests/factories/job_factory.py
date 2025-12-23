"""Test factory for creating Job instances."""
from datetime import datetime, timezone
from uuid import uuid4
from typing import Optional, Dict, Any
from sqlalchemy.orm import Session
from schedora.models.job import Job
from schedora.core.enums import JobStatus, RetryPolicy


def create_job(
    db: Session,
    job_type: str = "test_job",
    payload: Optional[Dict[str, Any]] = None,
    priority: int = 5,
    status: JobStatus = JobStatus.PENDING,
    max_retries: int = 3,
    retry_count: int = 0,
    retry_policy: RetryPolicy = RetryPolicy.EXPONENTIAL,
    idempotency_key: Optional[str] = None,
    **kwargs
) -> Job:
    """
    Factory function to create a Job for testing.

    Args:
        db: Database session
        job_type: Type of job
        payload: Job payload (defaults to empty dict)
        priority: Job priority (0-10)
        status: Initial job status
        max_retries: Maximum retry attempts
        retry_count: Current retry count
        retry_policy: Retry backoff policy
        idempotency_key: Unique key for idempotency (auto-generated if not provided)
        **kwargs: Additional fields to set on the job

    Returns:
        Job: Created job instance
    """
    if payload is None:
        payload = {}

    if idempotency_key is None:
        idempotency_key = f"test-key-{uuid4()}"

    job = Job(
        type=job_type,
        payload=payload,
        priority=priority,
        status=status,
        max_retries=max_retries,
        retry_count=retry_count,
        retry_policy=retry_policy,
        idempotency_key=idempotency_key,
        scheduled_at=kwargs.pop("scheduled_at", datetime.now(timezone.utc)),
        **kwargs
    )

    db.add(job)
    db.commit()
    db.refresh(job)

    return job
