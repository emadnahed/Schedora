"""API dependencies for FastAPI."""
from typing import Generator, Annotated
from fastapi import Depends
from sqlalchemy.orm import Session
from redis import Redis
from schedora.core.database import SessionLocal
from schedora.core.redis import get_redis
from schedora.services.job_service import JobService
from schedora.services.workflow_service import WorkflowService
from schedora.services.redis_queue import RedisQueue


def get_db() -> Generator[Session, None, None]:
    """
    Dependency to get database session.

    Yields:
        Session: SQLAlchemy database session
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_job_service(db: Annotated[Session, Depends(get_db)]) -> JobService:
    """
    Dependency to get JobService instance with Redis queue.

    Args:
        db: Database session (injected)

    Returns:
        JobService: Job service instance with queue
    """
    redis = get_redis()
    queue = RedisQueue(redis) if redis else None
    return JobService(db, queue=queue)


def get_workflow_service(db: Annotated[Session, Depends(get_db)]) -> WorkflowService:
    """
    Dependency to get WorkflowService instance.

    Args:
        db: Database session (injected)

    Returns:
        WorkflowService: Workflow service instance
    """
    return WorkflowService(db)


def get_redis_client() -> Redis:
    """
    Dependency to get Redis client.

    Returns:
        Redis: Redis client instance
    """
    return get_redis()
