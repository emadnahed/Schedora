"""Unit tests for Pydantic schemas."""
import pytest
from datetime import datetime, timezone
from uuid import uuid4
from pydantic import ValidationError
from schedora.api.schemas.job import JobCreate, JobResponse
from schedora.core.enums import JobStatus, RetryPolicy
from schedora.models.job import Job


class TestJobCreateSchema:
    """Test JobCreate schema validation."""

    def test_job_create_with_minimal_fields(self):
        """Test JobCreate with only required fields."""
        data = {
            "type": "test_job",
            "idempotency_key": "key-1",
        }

        schema = JobCreate(**data)

        assert schema.type == "test_job"
        assert schema.idempotency_key == "key-1"
        assert schema.priority == 5  # Default
        assert schema.max_retries == 3  # Default
        assert schema.retry_policy == RetryPolicy.EXPONENTIAL  # Default
        assert schema.payload == {}  # Default

    def test_job_create_with_all_fields(self):
        """Test JobCreate with all fields specified."""
        scheduled_time = datetime.now(timezone.utc)
        data = {
            "type": "email",
            "payload": {"to": "test@example.com"},
            "priority": 8,
            "scheduled_at": scheduled_time,
            "max_retries": 5,
            "retry_policy": RetryPolicy.FIXED,
            "timeout_seconds": 300,
            "idempotency_key": "key-123",
        }

        schema = JobCreate(**data)

        assert schema.type == "email"
        assert schema.priority == 8
        assert schema.max_retries == 5
        assert schema.retry_policy == RetryPolicy.FIXED
        assert schema.timeout_seconds == 300

    def test_job_create_priority_validation_min(self):
        """Test priority must be >= 0."""
        data = {
            "type": "test",
            "idempotency_key": "key-1",
            "priority": -1,
        }

        with pytest.raises(ValidationError) as exc_info:
            JobCreate(**data)
        assert "priority" in str(exc_info.value).lower()

    def test_job_create_priority_validation_max(self):
        """Test priority must be <= 10."""
        data = {
            "type": "test",
            "idempotency_key": "key-1",
            "priority": 11,
        }

        with pytest.raises(ValidationError):
            JobCreate(**data)

    def test_job_create_type_required(self):
        """Test type field is required."""
        data = {
            "idempotency_key": "key-1",
        }

        with pytest.raises(ValidationError) as exc_info:
            JobCreate(**data)
        assert "type" in str(exc_info.value).lower()

    def test_job_create_idempotency_key_required(self):
        """Test idempotency_key is required."""
        data = {
            "type": "test",
        }

        with pytest.raises(ValidationError) as exc_info:
            JobCreate(**data)
        assert "idempotency_key" in str(exc_info.value).lower()


class TestJobResponseSchema:
    """Test JobResponse schema."""

    def test_job_response_from_orm_model(self):
        """Test JobResponse can be created from ORM model."""
        job = Job(
            job_id=uuid4(),
            type="test",
            idempotency_key="key-1",
            payload={"test": "data"},
            priority=5,
            status=JobStatus.PENDING,
            max_retries=3,
            retry_count=0,
            retry_policy=RetryPolicy.EXPONENTIAL,
            scheduled_at=datetime.now(timezone.utc),
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )

        response = JobResponse.model_validate(job)

        assert str(response.job_id) == str(job.job_id)
        assert response.type == "test"
        assert response.status == JobStatus.PENDING

    def test_job_response_includes_all_fields(self):
        """Test JobResponse includes all expected fields."""
        job = Job(
            job_id=uuid4(),
            type="email",
            idempotency_key="key-1",
            payload={"to": "test@example.com"},
            priority=8,
            status=JobStatus.SUCCESS,
            max_retries=3,
            retry_count=1,
            retry_policy=RetryPolicy.FIXED,
            timeout_seconds=300,
            result={"sent": True},
            scheduled_at=datetime.now(timezone.utc),
            started_at=datetime.now(timezone.utc),
            completed_at=datetime.now(timezone.utc),
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )

        response = JobResponse.model_validate(job)

        assert response.priority == 8
        assert response.retry_count == 1
        assert response.result == {"sent": True}
        assert response.started_at is not None
        assert response.completed_at is not None
