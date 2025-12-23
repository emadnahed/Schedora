"""Workflow repository for data access operations."""
from typing import Optional, List, Dict, Any
from uuid import UUID
from sqlalchemy.orm import Session
from schedora.models.workflow import Workflow
from schedora.models.job import Job


class WorkflowRepository:
    """Repository for workflow data access operations."""

    def __init__(self, db: Session):
        """
        Initialize repository.

        Args:
            db: SQLAlchemy database session
        """
        self.db = db

    def create(
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

        Note:
            Transaction management is handled by the service layer.
        """
        workflow = Workflow(
            name=name,
            description=description,
            config=config
        )
        self.db.add(workflow)
        self.db.flush()  # Flush to get the ID without committing
        return workflow

    def get_by_id(self, workflow_id: UUID) -> Optional[Workflow]:
        """
        Get workflow by ID.

        Args:
            workflow_id: Workflow UUID

        Returns:
            Optional[Workflow]: Workflow if found, None otherwise
        """
        return self.db.query(Workflow).filter(Workflow.workflow_id == workflow_id).first()

    def get_by_name(self, name: str) -> Optional[Workflow]:
        """
        Get workflow by name.

        Args:
            name: Workflow name

        Returns:
            Optional[Workflow]: Workflow if found, None otherwise
        """
        return self.db.query(Workflow).filter(Workflow.name == name).first()

    def add_job(self, workflow_id: UUID, job_id: UUID) -> None:
        """
        Add a job to a workflow.

        Args:
            workflow_id: Workflow UUID
            job_id: Job UUID

        Note:
            Transaction management is handled by the service layer.
        """
        workflow = self.get_by_id(workflow_id)
        job = self.db.query(Job).filter(Job.job_id == job_id).first()

        if workflow and job:
            workflow.jobs.append(job)
            self.db.flush()

    def get_workflow_jobs(self, workflow_id: UUID) -> List[Job]:
        """
        Get all jobs associated with a workflow.

        Args:
            workflow_id: Workflow UUID

        Returns:
            List[Job]: List of jobs in the workflow
        """
        workflow = self.get_by_id(workflow_id)
        if workflow:
            return workflow.jobs
        return []

    def list_all(self, limit: int = 100) -> List[Workflow]:
        """
        List all workflows.

        Args:
            limit: Maximum number of workflows to return

        Returns:
            List[Workflow]: List of workflows
        """
        return self.db.query(Workflow).limit(limit).all()
