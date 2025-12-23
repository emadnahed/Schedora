"""Pydantic schemas for Job API."""
from datetime import datetime
from typing import Optional, Dict, Any
from uuid import UUID
from pydantic import BaseModel, Field
from schedora.core.enums import JobStatus, RetryPolicy


class JobCreate(BaseModel):
    """Schema for creating a new job."""

    type: str = Field(..., min_length=1, max_length=100, description="Job type")
    payload: Dict[str, Any] = Field(default_factory=dict, description="Job payload")
    priority: int = Field(default=5, ge=0, le=10, description="Job priority (0-10)")
    scheduled_at: Optional[datetime] = Field(default=None, description="Scheduled execution time")
    max_retries: int = Field(default=3, ge=0, description="Maximum retry attempts")
    retry_policy: RetryPolicy = Field(default=RetryPolicy.EXPONENTIAL, description="Retry backoff policy")
    timeout_seconds: Optional[int] = Field(default=None, gt=0, description="Execution timeout in seconds")
    idempotency_key: str = Field(..., min_length=1, max_length=255, description="Idempotency key")
    parent_job_id: Optional[UUID] = Field(default=None, description="Parent job ID for DAG workflows")

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "type": "send_email",
                    "payload": {"to": "user@example.com", "subject": "Hello"},
                    "priority": 5,
                    "max_retries": 3,
                    "idempotency_key": "email-123-456",
                }
            ]
        }
    }


class JobResponse(BaseModel):
    """Schema for job responses."""

    job_id: UUID
    type: str
    payload: Dict[str, Any]
    priority: int
    status: JobStatus
    scheduled_at: datetime
    max_retries: int
    retry_count: int
    retry_policy: RetryPolicy
    timeout_seconds: Optional[int]
    idempotency_key: str
    parent_job_id: Optional[UUID]
    started_at: Optional[datetime]
    completed_at: Optional[datetime]
    worker_id: Optional[str]
    error_message: Optional[str]
    result: Optional[Dict[str, Any]]
    created_at: datetime
    updated_at: datetime

    model_config = {
        "from_attributes": True,  # Pydantic v2: allow ORM model conversion
    }


class JobCancelResponse(BaseModel):
    """Response for job cancellation."""

    job_id: UUID
    status: JobStatus
    message: str


class ErrorResponse(BaseModel):
    """Standard error response."""

    detail: str
    error_code: Optional[str] = None
