"""Integration tests for Job service."""
import pytest
from uuid import uuid4
from schedora.services.job_service import JobService
from schedora.api.schemas.job import JobCreate
from schedora.core.enums import JobStatus
from schedora.core.exceptions import (
    JobNotFoundError,
    DuplicateIdempotencyKeyError,
    InvalidStateTransitionError,
)
from tests.factories.job_factory import create_job


class TestJobService:
    """Test Job service business logic."""

    def test_create_job_sets_defaults(self, db_session):
        """Test service sets default values on job creation."""
        service = JobService(db_session)
        job_data = JobCreate(
            type="test_job",
            idempotency_key="service-key-1",
        )

        job = service.create_job(job_data)

        assert job.status == JobStatus.PENDING
        assert job.priority == 5
        assert job.max_retries == 3
        assert job.retry_count == 0

    def test_create_job_duplicate_idempotency_key_raises(self, db_session):
        """Test creating job with duplicate idempotency key raises exception."""
        service = JobService(db_session)
        job_data = JobCreate(type="test", idempotency_key="duplicate-key")

        service.create_job(job_data)

        with pytest.raises(DuplicateIdempotencyKeyError) as exc_info:
            service.create_job(job_data)
        assert "duplicate-key" in str(exc_info.value).lower()

    def test_get_job_success(self, db_session):
        """Test getting existing job."""
        service = JobService(db_session)
        created_job = create_job(db_session, job_type="get_test")

        retrieved_job = service.get_job(created_job.job_id)

        assert retrieved_job.job_id == created_job.job_id
        assert retrieved_job.type == "get_test"

    def test_get_job_not_found_raises(self, db_session):
        """Test getting non-existent job raises exception."""
        service = JobService(db_session)
        fake_id = uuid4()

        with pytest.raises(JobNotFoundError):
            service.get_job(fake_id)

    def test_cancel_job_from_pending(self, db_session):
        """Test canceling pending job."""
        service = JobService(db_session)
        job = create_job(db_session, status=JobStatus.PENDING)

        canceled_job = service.cancel_job(job.job_id)

        assert canceled_job.status == JobStatus.CANCELED

    def test_cancel_job_from_terminal_state_raises(self, db_session):
        """Test canceling completed job raises exception."""
        service = JobService(db_session)
        job = create_job(db_session, status=JobStatus.SUCCESS)

        with pytest.raises(InvalidStateTransitionError):
            service.cancel_job(job.job_id)

    def test_transition_status_valid(self, db_session):
        """Test valid status transition."""
        service = JobService(db_session)
        job = create_job(db_session, status=JobStatus.PENDING)

        transitioned = service.transition_status(job.job_id, JobStatus.SCHEDULED)

        assert transitioned.status == JobStatus.SCHEDULED

    def test_transition_status_invalid_raises(self, db_session):
        """Test invalid status transition raises exception."""
        service = JobService(db_session)
        job = create_job(db_session, status=JobStatus.PENDING)

        with pytest.raises(InvalidStateTransitionError):
            # PENDING -> SUCCESS is invalid (must go through SCHEDULED, RUNNING)
            service.transition_status(job.job_id, JobStatus.SUCCESS)
