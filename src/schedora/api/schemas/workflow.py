"""Pydantic schemas for workflow API."""
from typing import Optional, Dict, Any
from uuid import UUID
from pydantic import BaseModel, Field


class WorkflowCreate(BaseModel):
    """Schema for creating a workflow."""

    name: str = Field(..., min_length=1, max_length=255, description="Workflow name (must be unique)")
    description: Optional[str] = Field(None, description="Optional workflow description")
    config: Optional[Dict[str, Any]] = Field(None, description="Optional JSONB configuration")

    model_config = {"from_attributes": True}


class WorkflowResponse(BaseModel):
    """Schema for workflow response."""

    workflow_id: UUID
    name: str
    description: Optional[str]
    config: Optional[Dict[str, Any]]

    model_config = {"from_attributes": True}


class WorkflowStatusResponse(BaseModel):
    """Schema for workflow status response."""

    workflow_id: str
    workflow_name: str
    total_jobs: int
    completed_jobs: int
    failed_jobs: int
    running_jobs: int
    status: str

    model_config = {"from_attributes": True}


class AddJobToWorkflowRequest(BaseModel):
    """Schema for adding a job to a workflow."""

    job_id: UUID = Field(..., description="Job UUID to add to workflow")

    model_config = {"from_attributes": True}
