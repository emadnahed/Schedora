"""Workflow API endpoints."""
from uuid import UUID
from typing import Annotated
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from schedora.api.deps import get_db
from schedora.api.schemas.workflow import (
    WorkflowCreate,
    WorkflowResponse,
    WorkflowStatusResponse,
    AddJobToWorkflowRequest
)
from schedora.services.workflow_service import WorkflowService
from schedora.core.exceptions import (
    DuplicateWorkflowError,
    WorkflowNotFoundError
)

router = APIRouter(prefix="/workflows", tags=["workflows"])


@router.post("", response_model=WorkflowResponse, status_code=status.HTTP_201_CREATED)
def create_workflow(
    workflow_data: WorkflowCreate,
    db: Annotated[Session, Depends(get_db)]
) -> WorkflowResponse:
    """
    Create a new workflow.

    Args:
        workflow_data: Workflow creation data
        db: Database session

    Returns:
        WorkflowResponse: Created workflow

    Raises:
        HTTPException: 409 if workflow with same name already exists
    """
    service = WorkflowService(db)

    try:
        workflow = service.create_workflow(
            name=workflow_data.name,
            description=workflow_data.description,
            config=workflow_data.config
        )
        return WorkflowResponse.model_validate(workflow)
    except DuplicateWorkflowError as e:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(e)
        )


@router.get("/{workflow_id}", response_model=WorkflowResponse)
def get_workflow(
    workflow_id: UUID,
    db: Annotated[Session, Depends(get_db)]
) -> WorkflowResponse:
    """
    Get workflow by ID.

    Args:
        workflow_id: Workflow UUID
        db: Database session

    Returns:
        WorkflowResponse: Workflow details

    Raises:
        HTTPException: 404 if workflow not found
    """
    service = WorkflowService(db)

    try:
        workflow = service.get_workflow(workflow_id)
        return WorkflowResponse.model_validate(workflow)
    except WorkflowNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )


@router.post("/{workflow_id}/jobs", status_code=status.HTTP_200_OK)
def add_job_to_workflow(
    workflow_id: UUID,
    job_data: AddJobToWorkflowRequest,
    db: Annotated[Session, Depends(get_db)]
) -> dict:
    """
    Add a job to a workflow.

    Args:
        workflow_id: Workflow UUID
        job_data: Job to add
        db: Database session

    Returns:
        dict: Success message

    Raises:
        HTTPException: 404 if workflow not found
    """
    service = WorkflowService(db)

    try:
        service.add_job_to_workflow(workflow_id, job_data.job_id)
        return {"message": "Job added to workflow successfully"}
    except WorkflowNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )


@router.get("/{workflow_id}/status", response_model=WorkflowStatusResponse)
def get_workflow_status(
    workflow_id: UUID,
    db: Annotated[Session, Depends(get_db)]
) -> WorkflowStatusResponse:
    """
    Get workflow execution status.

    Args:
        workflow_id: Workflow UUID
        db: Database session

    Returns:
        WorkflowStatusResponse: Workflow status with job counts

    Raises:
        HTTPException: 404 if workflow not found
    """
    service = WorkflowService(db)

    try:
        status_dict = service.get_workflow_status(workflow_id)
        return WorkflowStatusResponse(**status_dict)
    except WorkflowNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
