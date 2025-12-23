"""API tests for workflow endpoints."""
import pytest
from fastapi.testclient import TestClient
from tests.factories.job_factory import create_job
from schedora.core.enums import JobStatus


class TestWorkflowsAPI:
    """Test workflow API endpoints."""

    def test_create_workflow_success(self, client: TestClient):
        """Test creating a workflow successfully."""
        response = client.post(
            "/api/v1/workflows",
            json={
                "name": "test_workflow",
                "description": "Test workflow description"
            }
        )

        assert response.status_code == 201
        json_response = response.json()

        assert json_response["code"] == "WF_0001"
        assert json_response["httpStatus"] == "CREATED"

        data = json_response["data"]
        assert data["name"] == "test_workflow"
        assert data["description"] == "Test workflow description"
        assert "workflow_id" in data

    def test_create_workflow_with_config(self, client: TestClient):
        """Test creating workflow with config."""
        response = client.post(
            "/api/v1/workflows",
            json={
                "name": "config_workflow",
                "config": {"timeout": 3600, "retry": True}
            }
        )

        assert response.status_code == 201
        json_response = response.json()
        data = json_response["data"]

        assert data["config"]["timeout"] == 3600
        assert data["config"]["retry"] is True

    def test_create_workflow_minimal(self, client: TestClient):
        """Test creating workflow with only name."""
        response = client.post(
            "/api/v1/workflows",
            json={"name": "minimal_workflow"}
        )

        assert response.status_code == 201
        json_response = response.json()
        data = json_response["data"]

        assert data["name"] == "minimal_workflow"
        assert data["description"] is None

    def test_create_workflow_duplicate_name(self, client: TestClient):
        """Test creating workflow with duplicate name returns 409."""
        client.post("/api/v1/workflows", json={"name": "duplicate"})

        response = client.post("/api/v1/workflows", json={"name": "duplicate"})

        assert response.status_code == 409
        error_detail = response.json()["detail"]
        assert error_detail["code"] == "WF_4002"
        assert error_detail["httpStatus"] == "CONFLICT"
        assert "already exists" in error_detail["description"].lower()

    def test_create_workflow_validation_error(self, client: TestClient):
        """Test creating workflow without required fields returns 422."""
        response = client.post("/api/v1/workflows", json={})

        assert response.status_code == 422

    def test_get_workflow_success(self, client: TestClient, db_session):
        """Test getting workflow by ID."""
        # Create a workflow
        create_response = client.post(
            "/api/v1/workflows",
            json={"name": "get_workflow"}
        )
        workflow_id = create_response.json()["data"]["workflow_id"]

        # Get the workflow
        response = client.get(f"/api/v1/workflows/{workflow_id}")

        assert response.status_code == 200
        json_response = response.json()

        assert json_response["code"] == "WF_0002"
        assert json_response["httpStatus"] == "OK"

        data = json_response["data"]
        assert data["workflow_id"] == workflow_id
        assert data["name"] == "get_workflow"

    def test_get_workflow_not_found(self, client: TestClient):
        """Test getting non-existent workflow returns 404."""
        import uuid
        fake_id = str(uuid.uuid4())

        response = client.get(f"/api/v1/workflows/{fake_id}")

        assert response.status_code == 404
        error_detail = response.json()["detail"]
        assert error_detail["code"] == "WF_4001"
        assert error_detail["httpStatus"] == "NOT_FOUND"
        assert "not found" in error_detail["description"].lower()

    def test_get_workflow_invalid_uuid(self, client: TestClient):
        """Test getting workflow with invalid UUID returns 422."""
        response = client.get("/api/v1/workflows/not-a-uuid")

        assert response.status_code == 422

    def test_add_job_to_workflow_success(self, client: TestClient, db_session):
        """Test adding a job to a workflow."""
        # Create workflow
        wf_response = client.post(
            "/api/v1/workflows",
            json={"name": "add_job_workflow"}
        )
        workflow_id = wf_response.json()["data"]["workflow_id"]

        # Create job
        job = create_job(db_session, job_type="test", idempotency_key="api-job-1")

        # Add job to workflow
        response = client.post(
            f"/api/v1/workflows/{workflow_id}/jobs",
            json={"job_id": str(job.job_id)}
        )

        assert response.status_code == 200
        json_response = response.json()

        assert json_response["code"] == "WF_0004"
        assert json_response["httpStatus"] == "OK"
        assert json_response["data"]["message"] == "Job added to workflow successfully"

    def test_add_job_to_workflow_not_found(self, client: TestClient, db_session):
        """Test adding job to non-existent workflow returns 404."""
        import uuid
        fake_workflow_id = str(uuid.uuid4())
        job = create_job(db_session, job_type="test", idempotency_key="api-job-2")

        response = client.post(
            f"/api/v1/workflows/{fake_workflow_id}/jobs",
            json={"job_id": str(job.job_id)}
        )

        assert response.status_code == 404
        error_detail = response.json()["detail"]
        assert error_detail["code"] == "WF_4001"

    def test_get_workflow_status_success(self, client: TestClient, db_session):
        """Test getting workflow status."""
        # Create workflow
        wf_response = client.post(
            "/api/v1/workflows",
            json={"name": "status_workflow"}
        )
        workflow_id = wf_response.json()["data"]["workflow_id"]

        # Create and add jobs
        job1 = create_job(db_session, job_type="j1", status=JobStatus.SUCCESS, idempotency_key="status-1")
        job2 = create_job(db_session, job_type="j2", status=JobStatus.RUNNING, idempotency_key="status-2")

        client.post(f"/api/v1/workflows/{workflow_id}/jobs", json={"job_id": str(job1.job_id)})
        client.post(f"/api/v1/workflows/{workflow_id}/jobs", json={"job_id": str(job2.job_id)})

        # Get workflow status
        response = client.get(f"/api/v1/workflows/{workflow_id}/status")

        assert response.status_code == 200
        json_response = response.json()

        assert json_response["code"] == "WF_0003"
        assert json_response["httpStatus"] == "OK"

        data = json_response["data"]
        assert data["workflow_id"] == workflow_id
        assert data["workflow_name"] == "status_workflow"
        assert data["total_jobs"] == 2
        assert data["completed_jobs"] == 1
        assert data["running_jobs"] == 1
        assert data["status"] == "RUNNING"

    def test_get_workflow_status_not_found(self, client: TestClient):
        """Test getting status for non-existent workflow returns 404."""
        import uuid
        fake_id = str(uuid.uuid4())

        response = client.get(f"/api/v1/workflows/{fake_id}/status")

        assert response.status_code == 404
        error_detail = response.json()["detail"]
        assert error_detail["code"] == "WF_4001"
