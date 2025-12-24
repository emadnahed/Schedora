"""Integration tests for Workflow model."""
import pytest
from datetime import datetime, timezone
from schedora.models.workflow import Workflow
from schedora.core.enums import JobStatus
from tests.factories.job_factory import create_job


class TestWorkflowModel:
    """Test Workflow SQLAlchemy model."""

    def test_create_workflow_minimal(self, db_session):
        """Test creating workflow with minimal fields."""
        workflow = Workflow(
            name="test_workflow",
            description="Test workflow",
        )
        db_session.add(workflow)
        db_session.commit()
        db_session.refresh(workflow)

        assert workflow.workflow_id is not None
        assert workflow.name == "test_workflow"
        assert workflow.created_at is not None
        assert workflow.updated_at is not None

    def test_workflow_with_jobs(self, db_session):
        """Test workflow can have multiple jobs."""
        workflow = Workflow(
            name="order_processing",
            description="Order processing workflow",
        )
        db_session.add(workflow)
        db_session.commit()

        # Create jobs associated with workflow
        job1 = create_job(
            db_session,
            job_type="validate_order",
            idempotency_key="wf-job-1",
        )
        job2 = create_job(
            db_session,
            job_type="charge_payment",
            idempotency_key="wf-job-2",
        )

        # Associate jobs with workflow
        workflow.jobs.append(job1)
        workflow.jobs.append(job2)
        db_session.commit()
        db_session.refresh(workflow)

        assert len(workflow.jobs) == 2
        assert job1 in workflow.jobs
        assert job2 in workflow.jobs

    def test_workflow_name_unique(self, db_session):
        """Test workflow names must be unique."""
        workflow1 = Workflow(name="unique_workflow", description="First")
        db_session.add(workflow1)
        db_session.commit()

        workflow2 = Workflow(name="unique_workflow", description="Second")
        db_session.add(workflow2)

        from sqlalchemy.exc import IntegrityError
        with pytest.raises(IntegrityError):
            db_session.commit()

    def test_workflow_config_jsonb(self, db_session):
        """Test workflow can store config as JSONB."""
        config = {
            "timeout": 3600,
            "retry_failed_jobs": True,
            "notification_email": "admin@example.com",
        }

        workflow = Workflow(
            name="configurable_workflow",
            description="Workflow with config",
            config=config,
        )
        db_session.add(workflow)
        db_session.commit()
        db_session.refresh(workflow)

        assert workflow.config == config
        assert workflow.config["timeout"] == 3600
