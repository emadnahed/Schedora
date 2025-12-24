"""Pydantic schemas for worker API endpoints."""
from datetime import datetime
from typing import Optional, Dict, Any, List
from uuid import UUID
from pydantic import BaseModel, Field
from schedora.core.enums import WorkerStatus


class WorkerRegisterRequest(BaseModel):
    """Request schema for worker registration."""

    worker_id: str = Field(..., description="Unique worker identifier")
    hostname: str = Field(..., description="Worker hostname")
    pid: int = Field(..., description="Worker process ID")
    max_concurrent_jobs: int = Field(..., ge=1, description="Maximum concurrent jobs")
    version: str = Field(default="1.0.0", description="Worker version")
    capabilities: Optional[Dict[str, Any]] = Field(
        default=None, description="Worker capabilities"
    )
    metadata: Optional[Dict[str, Any]] = Field(
        default=None, description="Worker metadata"
    )


class WorkerHeartbeatRequest(BaseModel):
    """Request schema for worker heartbeat."""

    cpu_percent: Optional[float] = Field(None, ge=0, le=100, description="CPU usage %")
    memory_percent: Optional[float] = Field(
        None, ge=0, le=100, description="Memory usage %"
    )


class WorkerResponse(BaseModel):
    """Response schema for worker details."""

    worker_id: str
    hostname: str
    pid: int
    version: str
    status: WorkerStatus
    max_concurrent_jobs: int
    current_job_count: int
    started_at: datetime
    last_heartbeat_at: Optional[datetime] = None
    stopped_at: Optional[datetime] = None
    total_jobs_processed: int
    total_jobs_succeeded: int
    total_jobs_failed: int
    cpu_percent: Optional[float] = None
    memory_percent: Optional[float] = None
    capabilities: Optional[Dict[str, Any]] = None
    worker_metadata: Optional[Dict[str, Any]] = None

    class Config:
        from_attributes = True


class WorkerListResponse(BaseModel):
    """Response schema for list of workers."""

    workers: List[WorkerResponse]
    total: int


class WorkerJobsResponse(BaseModel):
    """Response schema for worker's current jobs."""

    worker_id: str
    job_ids: List[UUID]
    count: int
