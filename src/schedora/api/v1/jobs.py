"""Job API endpoints."""
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from schedora.api.deps import get_db
from schedora.api.schemas.job import JobCreate, JobResponse, JobCancelResponse
from schedora.api.schemas.response import StandardResponse, ResponseCodes
from schedora.services.job_service import JobService
from schedora.core.exceptions import (
    InvalidStateTransitionError,
    JobNotFoundError,
    DuplicateIdempotencyKeyError,
)

router = APIRouter()


@router.post("/jobs", response_model=StandardResponse[JobResponse], status_code=status.HTTP_201_CREATED)
async def create_job(
    job_data: JobCreate,
    db: Session = Depends(get_db),
) -> StandardResponse[JobResponse]:
    """
    Create a new job.

    - Validates job data
    - Ensures idempotency
    - Returns created job with job_id
    """
    try:
        job_service = JobService(db)
        job = job_service.create_job(job_data)
        return StandardResponse(
            data=JobResponse.model_validate(job),
            code=ResponseCodes.JOB_CREATED,
            httpStatus="CREATED",
            description="Job created successfully"
        )
    except DuplicateIdempotencyKeyError as e:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "data": None,
                "code": ResponseCodes.JOB_DUPLICATE_KEY,
                "httpStatus": "CONFLICT",
                "description": str(e)
            },
        )


@router.get("/jobs/{job_id}", response_model=StandardResponse[JobResponse])
async def get_job(
    job_id: UUID,
    db: Session = Depends(get_db),
) -> StandardResponse[JobResponse]:
    """
    Get job by ID.

    Returns full job details including current status.
    """
    try:
        job_service = JobService(db)
        job = job_service.get_job(job_id)
        return StandardResponse(
            data=JobResponse.model_validate(job),
            code=ResponseCodes.JOB_RETRIEVED,
            httpStatus="OK",
            description="Job retrieved successfully"
        )
    except JobNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "data": None,
                "code": ResponseCodes.JOB_NOT_FOUND,
                "httpStatus": "NOT_FOUND",
                "description": str(e)
            },
        )


@router.post("/jobs/{job_id}/cancel", response_model=StandardResponse[JobCancelResponse])
async def cancel_job(
    job_id: UUID,
    db: Session = Depends(get_db),
) -> StandardResponse[JobCancelResponse]:
    """
    Cancel a job.

    - Can only cancel non-terminal jobs
    - Returns updated job status
    """
    try:
        job_service = JobService(db)
        job = job_service.cancel_job(job_id)
        cancel_response = JobCancelResponse(
            job_id=job.job_id,
            status=job.status,
            message=f"Job {job_id} has been canceled",
        )
        return StandardResponse(
            data=cancel_response,
            code=ResponseCodes.JOB_CANCELED,
            httpStatus="OK",
            description="Job canceled successfully"
        )
    except JobNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "data": None,
                "code": ResponseCodes.JOB_NOT_FOUND,
                "httpStatus": "NOT_FOUND",
                "description": str(e)
            },
        )
    except InvalidStateTransitionError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "data": None,
                "code": ResponseCodes.JOB_INVALID_TRANSITION,
                "httpStatus": "BAD_REQUEST",
                "description": str(e)
            },
        )
