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
        data = response.json()
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
        assert "idempotency" in response2.json()["detail"].lower()

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
        data = response.json()
        assert data["job_id"] == str(job.job_id)
        assert data["type"] == "retrieve_test"

    def test_get_job_not_found(self, client: TestClient):
        """Test retrieving non-existent job returns 404."""
        fake_id = uuid4()
        response = client.get(f"/api/v1/jobs/{fake_id}")

        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()

    def test_cancel_job_success(self, client: TestClient, db_session):
        """Test canceling a pending job."""
        job = create_job(db_session, status=JobStatus.PENDING)

        response = client.post(f"/api/v1/jobs/{job.job_id}/cancel")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "CANCELED"
        assert "canceled" in data["message"].lower()

    def test_cancel_job_already_completed(self, client: TestClient, db_session):
        """Test canceling completed job fails."""
        job = create_job(db_session, status=JobStatus.SUCCESS)

        response = client.post(f"/api/v1/jobs/{job.job_id}/cancel")

        assert response.status_code == 400
        assert "transition" in response.json()["detail"].lower()

    def test_cancel_job_not_found(self, client: TestClient):
        """Test canceling non-existent job returns 404."""
        fake_id = uuid4()
        response = client.post(f"/api/v1/jobs/{fake_id}/cancel")

        assert response.status_code == 404
