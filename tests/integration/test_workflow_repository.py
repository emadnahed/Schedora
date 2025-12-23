"""Integration tests for workflow repository."""
import pytest
from schedora.repositories.workflow_repository import WorkflowRepository
from schedora.models.workflow import Workflow
from tests.factories.job_factory import create_job
from schedora.core.enums import JobStatus


class TestWorkflowRepository:
    """Test workflow repository CRUD operations."""

    def test_create_workflow(self, db_session):
        """Test creating a workflow."""
        repo = WorkflowRepository(db_session)

        workflow = repo.create(
            name="test_workflow",
            description="Test workflow description"
        )

        assert workflow.workflow_id is not None
        assert workflow.name == "test_workflow"
        assert workflow.description == "Test workflow description"
        assert workflow.created_at is not None

    def test_create_workflow_with_config(self, db_session):
        """Test creating workflow with JSONB config."""
        repo = WorkflowRepository(db_session)

        config = {
            "timeout": 3600,
            "retry_policy": "exponential",
            "notifications": {"email": "test@example.com"}
        }

        workflow = repo.create(
            name="config_workflow",
            config=config
        )

        assert workflow.config == config
        assert workflow.config["timeout"] == 3600

    def test_get_by_id_found(self, db_session):
        """Test getting workflow by ID when it exists."""
        repo = WorkflowRepository(db_session)

        workflow = repo.create(name="get_test")
        retrieved = repo.get_by_id(workflow.workflow_id)

        assert retrieved is not None
        assert retrieved.workflow_id == workflow.workflow_id
        assert retrieved.name == "get_test"

    def test_get_by_id_not_found(self, db_session):
        """Test getting workflow by ID when it doesn't exist."""
        import uuid
        repo = WorkflowRepository(db_session)

        retrieved = repo.get_by_id(uuid.uuid4())

        assert retrieved is None

    def test_get_by_name_found(self, db_session):
        """Test getting workflow by name when it exists."""
        repo = WorkflowRepository(db_session)

        workflow = repo.create(name="unique_name")
        retrieved = repo.get_by_name("unique_name")

        assert retrieved is not None
        assert retrieved.workflow_id == workflow.workflow_id

    def test_get_by_name_not_found(self, db_session):
        """Test getting workflow by name when it doesn't exist."""
        repo = WorkflowRepository(db_session)

        retrieved = repo.get_by_name("nonexistent")

        assert retrieved is None

    def test_add_job_to_workflow(self, db_session):
        """Test adding a job to a workflow."""
        repo = WorkflowRepository(db_session)

        workflow = repo.create(name="job_workflow")
        job = create_job(db_session, job_type="test", idempotency_key="add-job-1")

        repo.add_job(workflow.workflow_id, job.job_id)

        db_session.refresh(workflow)
        assert len(workflow.jobs) == 1
        assert workflow.jobs[0].job_id == job.job_id

    def test_add_multiple_jobs_to_workflow(self, db_session):
        """Test adding multiple jobs to a workflow."""
        repo = WorkflowRepository(db_session)

        workflow = repo.create(name="multi_job_workflow")
        job1 = create_job(db_session, job_type="job1", idempotency_key="multi-1")
        job2 = create_job(db_session, job_type="job2", idempotency_key="multi-2")

        repo.add_job(workflow.workflow_id, job1.job_id)
        repo.add_job(workflow.workflow_id, job2.job_id)

        db_session.refresh(workflow)
        assert len(workflow.jobs) == 2

    def test_get_workflow_jobs(self, db_session):
        """Test retrieving jobs associated with a workflow."""
        repo = WorkflowRepository(db_session)

        workflow = repo.create(name="get_jobs_workflow")
        job1 = create_job(db_session, job_type="job1", idempotency_key="get-1")
        job2 = create_job(db_session, job_type="job2", idempotency_key="get-2")

        repo.add_job(workflow.workflow_id, job1.job_id)
        repo.add_job(workflow.workflow_id, job2.job_id)

        jobs = repo.get_workflow_jobs(workflow.workflow_id)

        assert len(jobs) == 2
        job_ids = [job.job_id for job in jobs]
        assert job1.job_id in job_ids
        assert job2.job_id in job_ids

    def test_list_all_workflows(self, db_session):
        """Test listing all workflows."""
        repo = WorkflowRepository(db_session)

        repo.create(name="workflow1")
        repo.create(name="workflow2")
        repo.create(name="workflow3")

        workflows = repo.list_all()

        assert len(workflows) >= 3
        names = [w.name for w in workflows]
        assert "workflow1" in names
        assert "workflow2" in names
        assert "workflow3" in names
