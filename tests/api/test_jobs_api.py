"""API tests for job endpoints."""
import pytest
from uuid import uuid4
from fastapi.testclient import TestClient
from schedora.core.enums import JobStatus
from tests.factories.job_factory import create_job


class TestJobsAPI:
    """Test job API endpoints."""

    def test_create_job_success(self, client: TestClient, db_session):
        """Test successful job creation."""
        job_data = {
            "type": "email_notification",
            "payload": {"to": "test@example.com", "subject": "Test"},
            "priority": 5,
            "max_retries": 3,
            "idempotency_key": "api-test-key-1",
        }

        response = client.post("/api/v1/jobs", json=job_data)

        assert response.status_code == 201
        json_response = response.json()

        # Check standard response format
        assert "data" in json_response
        assert "code" in json_response
        assert "httpStatus" in json_response
        assert "description" in json_response

        assert json_response["code"] == "JOB_0001"
        assert json_response["httpStatus"] == "CREATED"

        # Check data payload
        data = json_response["data"]
        assert data["type"] == "email_notification"
        assert data["status"] == "PENDING"
        assert "job_id" in data
        assert data["retry_count"] == 0

    def test_create_job_duplicate_idempotency_key(self, client: TestClient, db_session):
        """Test creating job with duplicate idempotency key fails."""
        job_data = {
            "type": "test_job",
            "idempotency_key": "duplicate-api-key",
        }

        # First creation succeeds
        response1 = client.post("/api/v1/jobs", json=job_data)
        assert response1.status_code == 201

        # Second creation with same key fails
        response2 = client.post("/api/v1/jobs", json=job_data)
        assert response2.status_code == 409

        error_detail = response2.json()["detail"]
        assert error_detail["code"] == "JOB_4002"
        assert error_detail["httpStatus"] == "CONFLICT"
        assert "idempotency" in error_detail["description"].lower()

    def test_create_job_validation_error(self, client: TestClient):
        """Test job creation with invalid data."""
        job_data = {
            "type": "test",
            # Missing idempotency_key
        }

        response = client.post("/api/v1/jobs", json=job_data)
        assert response.status_code == 422  # Validation error

    def test_create_job_invalid_priority(self, client: TestClient):
        """Test job creation with invalid priority."""
        job_data = {
            "type": "test",
            "idempotency_key": "test-key",
            "priority": 11,  # Out of range
        }

        response = client.post("/api/v1/jobs", json=job_data)
        assert response.status_code == 422

    def test_get_job_success(self, client: TestClient, db_session):
        """Test retrieving an existing job."""
        job = create_job(db_session, job_type="retrieve_test")

        response = client.get(f"/api/v1/jobs/{job.job_id}")

        assert response.status_code == 200
        json_response = response.json()

        assert json_response["code"] == "JOB_0002"
        assert json_response["httpStatus"] == "OK"

        data = json_response["data"]
        assert data["job_id"] == str(job.job_id)
        assert data["type"] == "retrieve_test"

    def test_get_job_not_found(self, client: TestClient):
        """Test retrieving non-existent job returns 404."""
        fake_id = uuid4()
        response = client.get(f"/api/v1/jobs/{fake_id}")

        assert response.status_code == 404
        error_detail = response.json()["detail"]
        assert error_detail["code"] == "JOB_4001"
        assert error_detail["httpStatus"] == "NOT_FOUND"
        assert "not found" in error_detail["description"].lower()

    def test_cancel_job_success(self, client: TestClient, db_session):
        """Test canceling a pending job."""
        job = create_job(db_session, status=JobStatus.PENDING)

        response = client.post(f"/api/v1/jobs/{job.job_id}/cancel")

        assert response.status_code == 200
        json_response = response.json()

        assert json_response["code"] == "JOB_0003"
        assert json_response["httpStatus"] == "OK"

        data = json_response["data"]
        assert data["status"] == "CANCELED"
        assert "canceled" in data["message"].lower()

    def test_cancel_job_already_completed(self, client: TestClient, db_session):
        """Test canceling completed job fails."""
        job = create_job(db_session, status=JobStatus.SUCCESS)

        response = client.post(f"/api/v1/jobs/{job.job_id}/cancel")

        assert response.status_code == 400
        error_detail = response.json()["detail"]
        assert error_detail["code"] == "JOB_4003"
        assert error_detail["httpStatus"] == "BAD_REQUEST"
        assert "transition" in error_detail["description"].lower()

    def test_cancel_job_not_found(self, client: TestClient):
        """Test canceling non-existent job returns 404."""
        fake_id = uuid4()
        response = client.post(f"/api/v1/jobs/{fake_id}/cancel")

        assert response.status_code == 404
        error_detail = response.json()["detail"]
        assert error_detail["code"] == "JOB_4001"
