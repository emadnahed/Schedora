"""Workflow service for business logic."""
from typing import Optional, Dict, Any, List
from uuid import UUID
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from schedora.repositories.workflow_repository import WorkflowRepository
from schedora.models.workflow import Workflow
from schedora.core.exceptions import DuplicateWorkflowError, WorkflowNotFoundError
from schedora.core.enums import JobStatus


class WorkflowService:
    """Service for workflow business logic."""

    def __init__(self, db: Session):
        """
        Initialize workflow service.

        Args:
            db: SQLAlchemy database session
        """
        self.db = db
        self.repository = WorkflowRepository(db)

    def create_workflow(
        self,
        name: str,
        description: Optional[str] = None,
        config: Optional[Dict[str, Any]] = None
    ) -> Workflow:
        """
        Create a new workflow.

        Args:
            name: Workflow name (must be unique)
            description: Optional workflow description
            config: Optional JSONB configuration

        Returns:
            Workflow: Created workflow instance

        Raises:
            DuplicateWorkflowError: If workflow with same name already exists
        """
        # Check if workflow with same name exists
        existing = self.repository.get_by_name(name)
        if existing:
            raise DuplicateWorkflowError(f"Workflow with name '{name}' already exists")

        try:
            return self.repository.create(
                name=name,
                description=description,
                config=config
            )
        except IntegrityError as e:
            raise DuplicateWorkflowError(f"Workflow with name '{name}' already exists") from e

    def get_workflow(self, workflow_id: UUID) -> Workflow:
        """
        Get workflow by ID.

        Args:
            workflow_id: Workflow UUID

        Returns:
            Workflow: Workflow instance

        Raises:
            WorkflowNotFoundError: If workflow not found
        """
        workflow = self.repository.get_by_id(workflow_id)
        if not workflow:
            raise WorkflowNotFoundError(f"Workflow with ID {workflow_id} not found")
        return workflow

    def add_job_to_workflow(self, workflow_id: UUID, job_id: UUID) -> None:
        """
        Add a job to a workflow.

        Args:
            workflow_id: Workflow UUID
            job_id: Job UUID

        Raises:
            WorkflowNotFoundError: If workflow not found
        """
        workflow = self.get_workflow(workflow_id)
        self.repository.add_job(workflow_id, job_id)

    def get_workflow_status(self, workflow_id: UUID) -> Dict[str, Any]:
        """
        Get workflow execution status.

        Args:
            workflow_id: Workflow UUID

        Returns:
            Dict: Workflow status summary with job counts and overall status

        Raises:
            WorkflowNotFoundError: If workflow not found
        """
        workflow = self.get_workflow(workflow_id)
        jobs = workflow.jobs

        total_jobs = len(jobs)
        completed_jobs = sum(1 for job in jobs if job.status == JobStatus.SUCCESS)
        failed_jobs = sum(1 for job in jobs if job.status in [JobStatus.FAILED, JobStatus.DEAD, JobStatus.CANCELED])
        running_jobs = sum(1 for job in jobs if job.status in [JobStatus.RUNNING, JobStatus.SCHEDULED])

        # Determine overall workflow status
        if failed_jobs > 0:
            overall_status = "FAILED"
        elif completed_jobs == total_jobs and total_jobs > 0:
            overall_status = "COMPLETED"
        elif running_jobs > 0:
            overall_status = "RUNNING"
        else:
            overall_status = "PENDING"

        return {
            "workflow_id": str(workflow.workflow_id),
            "workflow_name": workflow.name,
            "total_jobs": total_jobs,
            "completed_jobs": completed_jobs,
            "failed_jobs": failed_jobs,
            "running_jobs": running_jobs,
            "status": overall_status
        }

    def list_workflows(self, limit: int = 100) -> List[Workflow]:
        """
        List all workflows.

        Args:
            limit: Maximum number of workflows to return

        Returns:
            List[Workflow]: List of workflows
        """
        return self.repository.list_all(limit=limit)
