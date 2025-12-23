"""Job API endpoints."""
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from schedora.api.deps import get_db
from schedora.api.schemas.job import JobCreate, JobResponse, JobCancelResponse
from schedora.services.job_service import JobService
from schedora.core.exceptions import (
    InvalidStateTransitionError,
    JobNotFoundError,
    DuplicateIdempotencyKeyError,
)

router = APIRouter()


@router.post("/jobs", response_model=JobResponse, status_code=status.HTTP_201_CREATED)
async def create_job(
    job_data: JobCreate,
    db: Session = Depends(get_db),
) -> JobResponse:
    """
    Create a new job.

    - Validates job data
    - Ensures idempotency
    - Returns created job with job_id
    """
    try:
        job_service = JobService(db)
        job = job_service.create_job(job_data)
        return JobResponse.model_validate(job)
    except DuplicateIdempotencyKeyError as e:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(e),
        )


@router.get("/jobs/{job_id}", response_model=JobResponse)
async def get_job(
    job_id: UUID,
    db: Session = Depends(get_db),
) -> JobResponse:
    """
    Get job by ID.

    Returns full job details including current status.
    """
    try:
        job_service = JobService(db)
        job = job_service.get_job(job_id)
        return JobResponse.model_validate(job)
    except JobNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )


@router.post("/jobs/{job_id}/cancel", response_model=JobCancelResponse)
async def cancel_job(
    job_id: UUID,
    db: Session = Depends(get_db),
) -> JobCancelResponse:
    """
    Cancel a job.

    - Can only cancel non-terminal jobs
    - Returns updated job status
    """
    try:
        job_service = JobService(db)
        job = job_service.cancel_job(job_id)
        return JobCancelResponse(
            job_id=job.job_id,
            status=job.status,
            message=f"Job {job_id} has been canceled",
        )
    except JobNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )
    except InvalidStateTransitionError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
