"""Worker API endpoints."""
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from redis import Redis
from schedora.api.deps import get_db, get_redis_client
from schedora.config import get_settings
from schedora.api.schemas.worker import (
    WorkerRegisterRequest,
    WorkerHeartbeatRequest,
    WorkerResponse,
    WorkerListResponse,
    WorkerJobsResponse,
)
from schedora.services.heartbeat_service import HeartbeatService
from schedora.repositories.worker_repository import WorkerRepository
from schedora.core.exceptions import WorkerNotFoundError
from schedora.models.worker import Worker
from schedora.core.enums import WorkerStatus

router = APIRouter(prefix="/workers", tags=["workers"])


@router.post("/register", response_model=WorkerResponse, status_code=status.HTTP_201_CREATED)
def register_worker(
    request: WorkerRegisterRequest,
    db: Session = Depends(get_db),
    redis: Redis = Depends(get_redis_client),
):
    """
    Register a new worker.

    Creates a worker record and initializes heartbeat tracking.
    """
    service = HeartbeatService(db, redis)

    try:
        worker = service.register_worker(
            worker_id=request.worker_id,
            hostname=request.hostname,
            pid=request.pid,
            max_concurrent_jobs=request.max_concurrent_jobs,
            version=request.version,
            capabilities=request.capabilities,
            metadata=request.metadata,
        )
        return WorkerResponse.model_validate(worker)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to register worker: {str(e)}",
        )


@router.post("/{worker_id}/heartbeat", status_code=status.HTTP_204_NO_CONTENT)
def send_heartbeat(
    worker_id: str,
    request: WorkerHeartbeatRequest,
    db: Session = Depends(get_db),
    redis: Redis = Depends(get_redis_client),
):
    """
    Send a heartbeat for a worker.

    Updates the worker's last heartbeat timestamp and metrics.
    """
    service = HeartbeatService(db, redis)
    repo = WorkerRepository(db)

    # Check worker exists
    worker = repo.get_by_id(worker_id)
    if not worker:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Worker {worker_id} not found",
        )

    service.send_heartbeat(
        worker_id=worker_id,
        cpu_percent=request.cpu_percent,
        memory_percent=request.memory_percent,
    )


@router.get("/{worker_id}", response_model=WorkerResponse)
def get_worker(
    worker_id: str,
    db: Session = Depends(get_db),
):
    """
    Get worker details by ID.
    """
    repo = WorkerRepository(db)
    worker = repo.get_by_id(worker_id)

    if not worker:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Worker {worker_id} not found",
        )

    return WorkerResponse.model_validate(worker)


@router.get("", response_model=WorkerListResponse)
def list_workers(
    status_filter: str = None,
    db: Session = Depends(get_db),
):
    """
    List all workers, optionally filtered by status.
    """
    repo = WorkerRepository(db)

    if status_filter == "active":
        workers = repo.get_all_active()
    elif status_filter == "stale":
        # Return workers with STALE status
        workers = db.query(Worker).filter(Worker.status == WorkerStatus.STALE).all()
    else:
        workers = repo.get_all()

    return WorkerListResponse(
        workers=[WorkerResponse.model_validate(w) for w in workers],
        total=len(workers),
    )


@router.get("/{worker_id}/jobs", response_model=WorkerJobsResponse)
def get_worker_jobs(
    worker_id: str,
    db: Session = Depends(get_db),
    redis: Redis = Depends(get_redis_client),
):
    """
    Get current jobs assigned to a worker.
    """
    repo = WorkerRepository(db)
    worker = repo.get_by_id(worker_id)

    if not worker:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Worker {worker_id} not found",
        )

    service = HeartbeatService(db, redis)
    job_ids = list(service.get_worker_jobs(worker_id))

    return WorkerJobsResponse(
        worker_id=worker_id,
        job_ids=job_ids,
        count=len(job_ids),
    )


@router.post("/{worker_id}/deregister", status_code=status.HTTP_204_NO_CONTENT)
def deregister_worker(
    worker_id: str,
    db: Session = Depends(get_db),
    redis: Redis = Depends(get_redis_client),
):
    """
    Deregister a worker (clean shutdown).

    Removes Redis keys and marks worker as STOPPED.
    """
    repo = WorkerRepository(db)
    worker = repo.get_by_id(worker_id)

    if not worker:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Worker {worker_id} not found",
        )

    service = HeartbeatService(db, redis)
    service.deregister_worker(worker_id)
