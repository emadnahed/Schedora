"""Integration tests for workflow service."""
import pytest
from schedora.services.workflow_service import WorkflowService
from schedora.core.exceptions import DuplicateWorkflowError, WorkflowNotFoundError
from tests.factories.job_factory import create_job
from schedora.core.enums import JobStatus


class TestWorkflowService:
    """Test workflow service business logic."""

    def test_create_workflow(self, db_session):
        """Test creating a workflow."""
        service = WorkflowService(db_session)

        workflow = service.create_workflow(
            name="test_workflow",
            description="Test description"
        )

        assert workflow.workflow_id is not None
        assert workflow.name == "test_workflow"
        assert workflow.description == "Test description"

    def test_create_workflow_with_config(self, db_session):
        """Test creating workflow with config."""
        service = WorkflowService(db_session)

        config = {"timeout": 3600, "retry": True}
        workflow = service.create_workflow(
            name="config_wf",
            config=config
        )

        assert workflow.config == config

    def test_create_duplicate_workflow_name_raises_error(self, db_session):
        """Test creating workflow with duplicate name raises error."""
        service = WorkflowService(db_session)

        service.create_workflow(name="duplicate")

        with pytest.raises(DuplicateWorkflowError):
            service.create_workflow(name="duplicate")

    def test_get_workflow_by_id(self, db_session):
        """Test getting workflow by ID."""
        service = WorkflowService(db_session)

        workflow = service.create_workflow(name="get_by_id")
        retrieved = service.get_workflow(workflow.workflow_id)

        assert retrieved.workflow_id == workflow.workflow_id
        assert retrieved.name == "get_by_id"

    def test_get_workflow_not_found_raises_error(self, db_session):
        """Test getting non-existent workflow raises error."""
        import uuid
        service = WorkflowService(db_session)

        with pytest.raises(WorkflowNotFoundError):
            service.get_workflow(uuid.uuid4())

    def test_add_job_to_workflow(self, db_session):
        """Test adding a job to a workflow."""
        service = WorkflowService(db_session)

        workflow = service.create_workflow(name="job_wf")
        job = create_job(db_session, job_type="test", idempotency_key="svc-1")

        service.add_job_to_workflow(workflow.workflow_id, job.job_id)

        retrieved = service.get_workflow(workflow.workflow_id)
        assert len(retrieved.jobs) == 1
        assert retrieved.jobs[0].job_id == job.job_id

    def test_get_workflow_status_all_pending(self, db_session):
        """Test getting workflow status when all jobs are pending."""
        service = WorkflowService(db_session)

        workflow = service.create_workflow(name="status_pending")
        job1 = create_job(db_session, job_type="j1", status=JobStatus.PENDING, idempotency_key="pend-1")
        job2 = create_job(db_session, job_type="j2", status=JobStatus.PENDING, idempotency_key="pend-2")

        service.add_job_to_workflow(workflow.workflow_id, job1.job_id)
        service.add_job_to_workflow(workflow.workflow_id, job2.job_id)

        status = service.get_workflow_status(workflow.workflow_id)

        assert status["workflow_id"] == str(workflow.workflow_id)
        assert status["workflow_name"] == "status_pending"
        assert status["total_jobs"] == 2
        assert status["completed_jobs"] == 0
        assert status["failed_jobs"] == 0
        assert status["running_jobs"] == 0
        assert status["status"] == "PENDING"

    def test_get_workflow_status_mixed(self, db_session):
        """Test getting workflow status with mixed job states."""
        service = WorkflowService(db_session)

        workflow = service.create_workflow(name="status_mixed")
        job1 = create_job(db_session, job_type="j1", status=JobStatus.SUCCESS, idempotency_key="mix-1")
        job2 = create_job(db_session, job_type="j2", status=JobStatus.RUNNING, idempotency_key="mix-2")
        job3 = create_job(db_session, job_type="j3", status=JobStatus.PENDING, idempotency_key="mix-3")

        service.add_job_to_workflow(workflow.workflow_id, job1.job_id)
        service.add_job_to_workflow(workflow.workflow_id, job2.job_id)
        service.add_job_to_workflow(workflow.workflow_id, job3.job_id)

        status = service.get_workflow_status(workflow.workflow_id)

        assert status["total_jobs"] == 3
        assert status["completed_jobs"] == 1
        assert status["running_jobs"] == 1
        assert status["status"] == "RUNNING"

    def test_get_workflow_status_all_complete(self, db_session):
        """Test getting workflow status when all jobs are complete."""
        service = WorkflowService(db_session)

        workflow = service.create_workflow(name="status_complete")
        job1 = create_job(db_session, job_type="j1", status=JobStatus.SUCCESS, idempotency_key="comp-1")
        job2 = create_job(db_session, job_type="j2", status=JobStatus.SUCCESS, idempotency_key="comp-2")

        service.add_job_to_workflow(workflow.workflow_id, job1.job_id)
        service.add_job_to_workflow(workflow.workflow_id, job2.job_id)

        status = service.get_workflow_status(workflow.workflow_id)

        assert status["total_jobs"] == 2
        assert status["completed_jobs"] == 2
        assert status["status"] == "COMPLETED"

    def test_get_workflow_status_with_failures(self, db_session):
        """Test getting workflow status with failed jobs."""
        service = WorkflowService(db_session)

        workflow = service.create_workflow(name="status_failed")
        job1 = create_job(db_session, job_type="j1", status=JobStatus.SUCCESS, idempotency_key="fail-1")
        job2 = create_job(db_session, job_type="j2", status=JobStatus.FAILED, idempotency_key="fail-2")

        service.add_job_to_workflow(workflow.workflow_id, job1.job_id)
        service.add_job_to_workflow(workflow.workflow_id, job2.job_id)

        status = service.get_workflow_status(workflow.workflow_id)

        assert status["completed_jobs"] == 1
        assert status["failed_jobs"] == 1
        assert status["status"] == "FAILED"

    def test_list_workflows(self, db_session):
        """Test listing all workflows."""
        service = WorkflowService(db_session)

        service.create_workflow(name="list1")
        service.create_workflow(name="list2")

        workflows = service.list_workflows()

        assert len(workflows) >= 2
        names = [w.name for w in workflows]
        assert "list1" in names
        assert "list2" in names
