"""Integration tests for job scheduler with atomic claiming."""
import pytest
from datetime import datetime, timedelta, timezone
from schedora.services.scheduler import Scheduler
from schedora.services.dependency_resolver import DependencyResolver
from schedora.core.enums import JobStatus
from tests.factories.job_factory import create_job


class TestScheduler:
    """Test scheduler with atomic job claiming."""

    def test_claim_single_ready_job(self, db_session):
        """Test claiming a single ready job."""
        scheduler = Scheduler(db_session)

        job = create_job(
            db_session,
            job_type="test_job",
            status=JobStatus.PENDING,
            scheduled_at=datetime.now(timezone.utc),
            idempotency_key="claim-1"
        )

        claimed = scheduler.claim_job()

        assert claimed is not None
        assert claimed.job_id == job.job_id
        assert claimed.status == JobStatus.SCHEDULED
        assert claimed.worker_id is not None

    def test_claim_job_with_future_scheduled_at(self, db_session):
        """Test job with future scheduled_at is not claimed."""
        scheduler = Scheduler(db_session)

        future_time = datetime.now(timezone.utc) + timedelta(hours=1)
        job = create_job(
            db_session,
            job_type="future_job",
            status=JobStatus.PENDING,
            scheduled_at=future_time,
            idempotency_key="future-1"
        )

        claimed = scheduler.claim_job()

        assert claimed is None
        db_session.refresh(job)
        assert job.status == JobStatus.PENDING

    def test_claim_job_respects_dependencies(self, db_session):
        """Test scheduler respects job dependencies."""
        scheduler = Scheduler(db_session)

        dep = create_job(
            db_session,
            job_type="dependency",
            status=JobStatus.RUNNING,
            idempotency_key="dep-claim-1"
        )

        job = create_job(
            db_session,
            job_type="dependent_job",
            status=JobStatus.PENDING,
            scheduled_at=datetime.now(timezone.utc),
            idempotency_key="dependent-1"
        )
        job.dependencies.append(dep)
        db_session.commit()

        claimed = scheduler.claim_job()

        # Should not claim job with unmet dependencies
        assert claimed is None
        db_session.refresh(job)
        assert job.status == JobStatus.PENDING

    def test_claim_job_with_met_dependencies(self, db_session):
        """Test scheduler claims job when dependencies are met."""
        scheduler = Scheduler(db_session)

        dep = create_job(
            db_session,
            job_type="dependency",
            status=JobStatus.SUCCESS,
            idempotency_key="dep-met-1"
        )

        job = create_job(
            db_session,
            job_type="dependent_job",
            status=JobStatus.PENDING,
            scheduled_at=datetime.now(timezone.utc),
            idempotency_key="dependent-met-1"
        )
        job.dependencies.append(dep)
        db_session.commit()

        claimed = scheduler.claim_job()

        assert claimed is not None
        assert claimed.job_id == job.job_id
        assert claimed.status == JobStatus.SCHEDULED

    def test_claim_no_pending_jobs(self, db_session):
        """Test claiming when no pending jobs exist."""
        scheduler = Scheduler(db_session)

        # Create only completed jobs
        create_job(db_session, job_type="done", status=JobStatus.SUCCESS, idempotency_key="done-1")

        claimed = scheduler.claim_job()

        assert claimed is None

    def test_claim_batch_of_jobs(self, db_session):
        """Test claiming multiple jobs in batch."""
        scheduler = Scheduler(db_session)

        job1 = create_job(
            db_session,
            job_type="batch1",
            status=JobStatus.PENDING,
            scheduled_at=datetime.now(timezone.utc),
            idempotency_key="batch-1"
        )
        job2 = create_job(
            db_session,
            job_type="batch2",
            status=JobStatus.PENDING,
            scheduled_at=datetime.now(timezone.utc),
            idempotency_key="batch-2"
        )
        job3 = create_job(
            db_session,
            job_type="batch3",
            status=JobStatus.PENDING,
            scheduled_at=datetime.now(timezone.utc),
            idempotency_key="batch-3"
        )

        claimed = scheduler.claim_ready_jobs(limit=2)

        assert len(claimed) == 2
        assert all(j.status == JobStatus.SCHEDULED for j in claimed)
        assert all(j.worker_id is not None for j in claimed)

    def test_claim_jobs_skips_running(self, db_session):
        """Test claiming skips jobs already running."""
        scheduler = Scheduler(db_session)

        job1 = create_job(
            db_session,
            job_type="running",
            status=JobStatus.RUNNING,
            scheduled_at=datetime.now(timezone.utc),
            idempotency_key="running-1"
        )
        job2 = create_job(
            db_session,
            job_type="pending",
            status=JobStatus.PENDING,
            scheduled_at=datetime.now(timezone.utc),
            idempotency_key="pending-skip-1"
        )

        claimed = scheduler.claim_job()

        assert claimed is not None
        assert claimed.job_id == job2.job_id

    def test_concurrent_claim_no_duplicates(self, db_session):
        """Test claimed job cannot be claimed again."""
        scheduler1 = Scheduler(db_session, worker_id="worker-1")
        scheduler2 = Scheduler(db_session, worker_id="worker-2")

        job = create_job(
            db_session,
            job_type="concurrent",
            status=JobStatus.PENDING,
            scheduled_at=datetime.now(timezone.utc),
            idempotency_key="concurrent-1"
        )

        # First scheduler claims the job
        claimed1 = scheduler1.claim_job()

        assert claimed1 is not None
        assert claimed1.status == JobStatus.SCHEDULED
        assert claimed1.worker_id == "worker-1"

        # Second scheduler should not claim the same job since it's already scheduled
        claimed2 = scheduler2.claim_job()

        assert claimed2 is None

    def test_worker_id_assigned_on_claim(self, db_session):
        """Test worker_id is assigned when job is claimed."""
        scheduler = Scheduler(db_session, worker_id="worker-123")

        job = create_job(
            db_session,
            job_type="worker_test",
            status=JobStatus.PENDING,
            scheduled_at=datetime.now(timezone.utc),
            idempotency_key="worker-1"
        )

        claimed = scheduler.claim_job()

        assert claimed.worker_id == "worker-123"
