"""Integration tests for Job model."""
import pytest
from datetime import datetime, timezone
from uuid import uuid4
from sqlalchemy.exc import IntegrityError
from schedora.models.job import Job
from schedora.core.enums import JobStatus, RetryPolicy


class TestJobModel:
    """Test Job SQLAlchemy model."""

    def test_create_job_with_minimal_fields(self, db_session):
        """Test creating job with only required fields."""
        job = Job(
            type="test_job",
            idempotency_key="test-key-1",
            payload={"test": "data"},
        )
        db_session.add(job)
        db_session.commit()
        db_session.refresh(job)

        assert job.job_id is not None
        assert job.type == "test_job"
        assert job.idempotency_key == "test-key-1"
        assert job.status == JobStatus.PENDING
        assert job.priority == 5
        assert job.max_retries == 3
        assert job.retry_count == 0
        assert job.created_at is not None
        assert job.updated_at is not None

    def test_create_job_with_all_fields(self, db_session):
        """Test creating job with all fields specified."""
        scheduled_time = datetime.now(timezone.utc)
        job = Job(
            type="email",
            payload={"to": "test@example.com"},
            priority=8,
            scheduled_at=scheduled_time,
            max_retries=5,
            retry_policy=RetryPolicy.EXPONENTIAL,
            timeout_seconds=300,
            idempotency_key="key-123",
            status=JobStatus.SCHEDULED,
        )
        db_session.add(job)
        db_session.commit()
        db_session.refresh(job)

        assert job.type == "email"
        assert job.priority == 8
        assert job.max_retries == 5
        assert job.retry_policy == RetryPolicy.EXPONENTIAL
        assert job.timeout_seconds == 300
        assert job.status == JobStatus.SCHEDULED

    def test_idempotency_key_unique_constraint(self, db_session):
        """Test that duplicate idempotency keys are rejected."""
        job1 = Job(
            type="test",
            idempotency_key="duplicate-key",
            payload={},
        )
        db_session.add(job1)
        db_session.commit()

        job2 = Job(
            type="test",
            idempotency_key="duplicate-key",
            payload={},
        )
        db_session.add(job2)

        with pytest.raises(IntegrityError) as exc_info:
            db_session.commit()
        assert "idempotency_key" in str(exc_info.value).lower()

    def test_priority_within_valid_range(self, db_session):
        """Test that priority can be set within valid range (0-10)."""
        for priority in [0, 5, 10]:
            job = Job(
                type="test",
                idempotency_key=f"key-priority-{priority}",
                priority=priority,
                payload={},
            )
            db_session.add(job)
            db_session.commit()
            assert job.priority == priority

    def test_job_status_values(self, db_session):
        """Test that all valid job statuses can be set."""
        statuses = [
            JobStatus.PENDING,
            JobStatus.SCHEDULED,
            JobStatus.RUNNING,
            JobStatus.SUCCESS,
            JobStatus.FAILED,
        ]

        for idx, status in enumerate(statuses):
            job = Job(
                type="test",
                idempotency_key=f"key-status-{idx}",
                status=status,
                payload={},
            )
            db_session.add(job)
            db_session.commit()
            db_session.refresh(job)
            assert job.status == status

    def test_retry_policy_values(self, db_session):
        """Test that all retry policies can be set."""
        policies = [RetryPolicy.FIXED, RetryPolicy.EXPONENTIAL, RetryPolicy.JITTER]

        for idx, policy in enumerate(policies):
            job = Job(
                type="test",
                idempotency_key=f"key-policy-{idx}",
                retry_policy=policy,
                payload={},
            )
            db_session.add(job)
            db_session.commit()
            db_session.refresh(job)
            assert job.retry_policy == policy

    def test_payload_jsonb_storage(self, db_session):
        """Test that complex payloads are stored correctly as JSONB."""
        complex_payload = {
            "user_id": 123,
            "action": "send_email",
            "data": {
                "to": ["user1@example.com", "user2@example.com"],
                "subject": "Test",
                "body": "Hello World",
            },
            "metadata": {"timestamp": "2024-01-01T00:00:00Z", "source": "api"},
        }

        job = Job(
            type="email",
            idempotency_key="complex-payload",
            payload=complex_payload,
        )
        db_session.add(job)
        db_session.commit()
        db_session.refresh(job)

        assert job.payload == complex_payload
        assert job.payload["data"]["to"] == ["user1@example.com", "user2@example.com"]

    def test_timestamps_auto_populated(self, db_session):
        """Test that created_at and updated_at are automatically set."""
        job = Job(
            type="test",
            idempotency_key="timestamp-test",
            payload={},
        )
        db_session.add(job)
        db_session.commit()
        db_session.refresh(job)

        assert job.created_at is not None
        assert job.updated_at is not None
        assert isinstance(job.created_at, datetime)
        assert isinstance(job.updated_at, datetime)

    def test_update_status_updates_timestamp(self, db_session):
        """Test that updating job updates the updated_at timestamp."""
        job = Job(
            type="test",
            idempotency_key="update-test",
            payload={},
        )
        db_session.add(job)
        db_session.commit()
        db_session.refresh(job)

        original_updated_at = job.updated_at

        # Small delay to ensure timestamp difference
        import time

        time.sleep(0.01)

        # Update job status
        job.status = JobStatus.RUNNING
        db_session.commit()
        db_session.refresh(job)

        assert job.updated_at > original_updated_at

    def test_job_id_is_uuid(self, db_session):
        """Test that job_id is a valid UUID."""
        job = Job(
            type="test",
            idempotency_key="uuid-test",
            payload={},
        )
        db_session.add(job)
        db_session.commit()
        db_session.refresh(job)

        assert job.job_id is not None
        # Should be able to convert to string and back
        from uuid import UUID

        uuid_obj = UUID(str(job.job_id))
        assert uuid_obj == job.job_id

    def test_error_details_jsonb_storage(self, db_session):
        """Test that error details are stored as JSONB."""
        error_details = {
            "error_type": "ValueError",
            "stack_trace": "line 1\nline 2\nline 3",
            "context": {"attempt": 1, "max_retries": 3},
        }

        job = Job(
            type="test",
            idempotency_key="error-test",
            payload={},
            status=JobStatus.FAILED,
            error_message="Test error",
            error_details=error_details,
        )
        db_session.add(job)
        db_session.commit()
        db_session.refresh(job)

        assert job.error_message == "Test error"
        assert job.error_details == error_details

    def test_result_jsonb_storage(self, db_session):
        """Test that job results are stored as JSONB."""
        result_data = {
            "status": "completed",
            "records_processed": 150,
            "output": {"file_url": "https://example.com/result.csv"},
        }

        job = Job(
            type="etl",
            idempotency_key="result-test",
            payload={},
            status=JobStatus.SUCCESS,
            result=result_data,
        )
        db_session.add(job)
        db_session.commit()
        db_session.refresh(job)

        assert job.result == result_data
        assert job.result["records_processed"] == 150
