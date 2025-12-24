"""Queue management API endpoints."""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from schedora.services.redis_queue import RedisQueue
from schedora.core.redis import get_redis


router = APIRouter(prefix="/queue", tags=["queue"])


class QueueStatsResponse(BaseModel):
    """Response for queue statistics."""

    pending_jobs: int
    dlq_jobs: int


class QueuePurgeResponse(BaseModel):
    """Response for queue purge operation."""

    message: str


class QueuePeekResponse(BaseModel):
    """Response for queue peek operation."""

    job_id: str


@router.get("/stats", response_model=QueueStatsResponse)
def get_queue_stats():
    """
    Get queue statistics.

    Returns:
        QueueStatsResponse: Queue and DLQ lengths
    """
    redis = get_redis()
    if not redis:
        raise HTTPException(status_code=503, detail="Redis not available")

    queue = RedisQueue(redis)

    return QueueStatsResponse(
        pending_jobs=queue.get_queue_length(),
        dlq_jobs=queue.get_dlq_length(),
    )


@router.post("/purge", response_model=QueuePurgeResponse)
def purge_queue():
    """
    Purge all jobs from the main queue.

    WARNING: This is a destructive operation that removes all pending jobs.

    Returns:
        QueuePurgeResponse: Success message
    """
    redis = get_redis()
    if not redis:
        raise HTTPException(status_code=503, detail="Redis not available")

    queue = RedisQueue(redis)
    queue.purge()

    return QueuePurgeResponse(message="Queue purged successfully")


@router.post("/dlq/purge", response_model=QueuePurgeResponse)
def purge_dlq():
    """
    Purge all jobs from the dead letter queue.

    WARNING: This is a destructive operation that removes all failed jobs.

    Returns:
        QueuePurgeResponse: Success message
    """
    redis = get_redis()
    if not redis:
        raise HTTPException(status_code=503, detail="Redis not available")

    queue = RedisQueue(redis)
    queue.purge_dlq()

    return QueuePurgeResponse(message="DLQ purged successfully")


@router.get("/peek", response_model=QueuePeekResponse)
def peek_next_job():
    """
    Peek at the next job in queue without removing it.

    Returns:
        QueuePeekResponse: Job ID of next job

    Raises:
        HTTPException: 404 if queue is empty
    """
    redis = get_redis()
    if not redis:
        raise HTTPException(status_code=503, detail="Redis not available")

    queue = RedisQueue(redis)
    job_id = queue.peek()

    if not job_id:
        raise HTTPException(status_code=404, detail="No jobs in queue")

    return QueuePeekResponse(job_id=str(job_id))
