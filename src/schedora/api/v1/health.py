"""Health check API endpoint."""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import text
from redis import Redis
from pydantic import BaseModel
from typing import Optional
from schedora.api.deps import get_db, get_redis_client
from schedora.api.schemas.response import StandardResponse, ResponseCodes
from schedora.repositories.worker_repository import WorkerRepository
from schedora.models.worker import Worker
from schedora.core.enums import WorkerStatus

router = APIRouter()


class WorkerStats(BaseModel):
    """Worker statistics."""

    total: int
    active: int
    stale: int


class HealthData(BaseModel):
    """Health check data model."""

    status: str
    database: str
    redis: str
    workers: Optional[WorkerStats] = None


@router.get("/health", response_model=StandardResponse[HealthData])
async def health_check(
    db: Session = Depends(get_db),
    redis: Redis = Depends(get_redis_client),
) -> StandardResponse[HealthData]:
    """
    Health check endpoint.

    Returns:
        StandardResponse: Service health status including database, Redis, and worker statistics
    """
    # Check database connection
    try:
        db.execute(text("SELECT 1"))
        db_status = "connected"
    except Exception:
        db_status = "disconnected"

    # Check Redis connection
    try:
        redis.ping()
        redis_status = "connected"
    except Exception:
        redis_status = "disconnected"

    # Get worker statistics
    worker_stats = None
    try:
        repo = WorkerRepository(db)
        all_workers = repo.get_all()
        active_workers = repo.get_all_active()
        stale_workers = db.query(Worker).filter(Worker.status == WorkerStatus.STALE).all()

        worker_stats = WorkerStats(
            total=len(all_workers),
            active=len(active_workers),
            stale=len(stale_workers),
        )
    except Exception:
        pass  # Worker stats are optional

    overall_status = "healthy"
    if db_status != "connected" or redis_status != "connected":
        overall_status = "unhealthy"

    health_data = HealthData(
        status=overall_status,
        database=db_status,
        redis=redis_status,
        workers=worker_stats,
    )

    return StandardResponse(
        data=health_data,
        code=ResponseCodes.HEALTH_OK,
        httpStatus="OK",
        description="Health check completed successfully",
    )
