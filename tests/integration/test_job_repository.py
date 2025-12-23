"""Integration tests for Job repository."""
import pytest
from uuid import uuid4
from schedora.repositories.job_repository import JobRepository
from schedora.core.enums import JobStatus
from schedora.core.exceptions import JobNotFoundError
from tests.factories.job_factory import create_job


class TestJobRepository:
    """Test Job repository data access layer."""

    def test_create_job(self, db_session):
        """Test repository creates job correctly."""
        repo = JobRepository(db_session)
        job_data = {
            "type": "test_job",
            "idempotency_key": "repo-test-1",
            "payload": {"test": "data"},
            "priority": 7,
        }

        job = repo.create(job_data)

        assert job.job_id is not None
        assert job.type == "test_job"
        assert job.priority == 7
        assert job.status == JobStatus.PENDING

    def test_get_by_id_found(self, db_session):
        """Test repository retrieves job by ID."""
        repo = JobRepository(db_session)
        created_job = create_job(db_session, job_type="retrieve_test")

        retrieved_job = repo.get_by_id(created_job.job_id)

        assert retrieved_job is not None
        assert retrieved_job.job_id == created_job.job_id
        assert retrieved_job.type == "retrieve_test"

    def test_get_by_id_not_found(self, db_session):
        """Test repository returns None for non-existent job."""
        repo = JobRepository(db_session)
        fake_id = uuid4()

        result = repo.get_by_id(fake_id)

        assert result is None

    def test_update_status(self, db_session):
        """Test repository updates job status."""
        repo = JobRepository(db_session)
        job = create_job(db_session, status=JobStatus.PENDING)

        updated_job = repo.update_status(job.job_id, JobStatus.RUNNING)

        assert updated_job.status == JobStatus.RUNNING

    def test_update_status_not_found_raises(self, db_session):
        """Test updating non-existent job raises error."""
        repo = JobRepository(db_session)
        fake_id = uuid4()

        with pytest.raises(JobNotFoundError):
            repo.update_status(fake_id, JobStatus.RUNNING)

    def test_get_by_idempotency_key(self, db_session):
        """Test retrieving job by idempotency key."""
        repo = JobRepository(db_session)
        job = create_job(db_session, idempotency_key="unique-key-123")

        retrieved = repo.get_by_idempotency_key("unique-key-123")

        assert retrieved is not None
        assert retrieved.job_id == job.job_id

    def test_get_by_idempotency_key_not_found(self, db_session):
        """Test retrieving non-existent idempotency key returns None."""
        repo = JobRepository(db_session)

        result = repo.get_by_idempotency_key("non-existent")

        assert result is None
