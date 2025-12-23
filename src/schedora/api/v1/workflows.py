"""Workflow API endpoints."""
from uuid import UUID
from typing import Annotated, Dict
from fastapi import APIRouter, Depends, HTTPException, status

from schedora.api.deps import get_workflow_service
from schedora.api.schemas.workflow import (
    WorkflowCreate,
    WorkflowResponse,
    WorkflowStatusResponse,
    AddJobToWorkflowRequest
)
from schedora.api.schemas.response import StandardResponse, ResponseCodes
from schedora.services.workflow_service import WorkflowService
from schedora.core.exceptions import (
    DuplicateWorkflowError,
    WorkflowNotFoundError
)

router = APIRouter(prefix="/workflows", tags=["workflows"])


@router.post("", response_model=StandardResponse[WorkflowResponse], status_code=status.HTTP_201_CREATED)
def create_workflow(
    workflow_data: WorkflowCreate,
    service: Annotated[WorkflowService, Depends(get_workflow_service)]
) -> StandardResponse[WorkflowResponse]:
    """
    Create a new workflow.

    Args:
        workflow_data: Workflow creation data
        service: Workflow service (injected)

    Returns:
        StandardResponse: Created workflow

    Raises:
        HTTPException: 409 if workflow with same name already exists
    """

    try:
        workflow = service.create_workflow(
            name=workflow_data.name,
            description=workflow_data.description,
            config=workflow_data.config
        )
        return StandardResponse(
            data=WorkflowResponse.model_validate(workflow),
            code=ResponseCodes.WORKFLOW_CREATED,
            httpStatus="CREATED",
            description="Workflow created successfully"
        )
    except DuplicateWorkflowError as e:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "data": None,
                "code": ResponseCodes.WORKFLOW_DUPLICATE_NAME,
                "httpStatus": "CONFLICT",
                "description": str(e)
            }
        )


@router.get("/{workflow_id}", response_model=StandardResponse[WorkflowResponse])
def get_workflow(
    workflow_id: UUID,
    service: Annotated[WorkflowService, Depends(get_workflow_service)]
) -> StandardResponse[WorkflowResponse]:
    """
    Get workflow by ID.

    Args:
        workflow_id: Workflow UUID
        service: Workflow service (injected)

    Returns:
        StandardResponse: Workflow details

    Raises:
        HTTPException: 404 if workflow not found
    """

    try:
        workflow = service.get_workflow(workflow_id)
        return StandardResponse(
            data=WorkflowResponse.model_validate(workflow),
            code=ResponseCodes.WORKFLOW_RETRIEVED,
            httpStatus="OK",
            description="Workflow retrieved successfully"
        )
    except WorkflowNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "data": None,
                "code": ResponseCodes.WORKFLOW_NOT_FOUND,
                "httpStatus": "NOT_FOUND",
                "description": str(e)
            }
        )


@router.post("/{workflow_id}/jobs", response_model=StandardResponse[Dict[str, str]])
def add_job_to_workflow(
    workflow_id: UUID,
    job_data: AddJobToWorkflowRequest,
    service: Annotated[WorkflowService, Depends(get_workflow_service)]
) -> StandardResponse[Dict[str, str]]:
    """
    Add a job to a workflow.

    Args:
        workflow_id: Workflow UUID
        job_data: Job to add
        service: Workflow service (injected)

    Returns:
        StandardResponse: Success message

    Raises:
        HTTPException: 404 if workflow not found
    """

    try:
        service.add_job_to_workflow(workflow_id, job_data.job_id)
        return StandardResponse(
            data={"message": "Job added to workflow successfully"},
            code=ResponseCodes.JOB_ADDED_TO_WORKFLOW,
            httpStatus="OK",
            description="Job added to workflow successfully"
        )
    except WorkflowNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "data": None,
                "code": ResponseCodes.WORKFLOW_NOT_FOUND,
                "httpStatus": "NOT_FOUND",
                "description": str(e)
            }
        )


@router.get("/{workflow_id}/status", response_model=StandardResponse[WorkflowStatusResponse])
def get_workflow_status(
    workflow_id: UUID,
    service: Annotated[WorkflowService, Depends(get_workflow_service)]
) -> StandardResponse[WorkflowStatusResponse]:
    """
    Get workflow execution status.

    Args:
        workflow_id: Workflow UUID
        service: Workflow service (injected)

    Returns:
        StandardResponse: Workflow status with job counts

    Raises:
        HTTPException: 404 if workflow not found
    """

    try:
        status_dict = service.get_workflow_status(workflow_id)
        return StandardResponse(
            data=WorkflowStatusResponse(**status_dict),
            code=ResponseCodes.WORKFLOW_STATUS_RETRIEVED,
            httpStatus="OK",
            description="Workflow status retrieved successfully"
        )
    except WorkflowNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "data": None,
                "code": ResponseCodes.WORKFLOW_NOT_FOUND,
                "httpStatus": "NOT_FOUND",
                "description": str(e)
            }
        )
