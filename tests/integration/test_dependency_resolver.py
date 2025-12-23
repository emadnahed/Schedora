"""Integration tests for dependency resolution."""
import pytest
from schedora.services.dependency_resolver import DependencyResolver
from schedora.core.enums import JobStatus
from tests.factories.job_factory import create_job


class TestDependencyResolver:
    """Test dependency resolution logic."""

    def test_job_with_no_dependencies_is_ready(self, db_session):
        """Test job with no dependencies is ready to execute."""
        resolver = DependencyResolver(db_session)
        job = create_job(db_session, job_type="standalone", idempotency_key="no-deps-1")

        assert resolver.are_dependencies_met(job) is True

    def test_job_with_successful_dependencies_is_ready(self, db_session):
        """Test job is ready when all dependencies succeeded."""
        resolver = DependencyResolver(db_session)

        dep1 = create_job(db_session, job_type="dep1", status=JobStatus.SUCCESS, idempotency_key="dep-1")
        dep2 = create_job(db_session, job_type="dep2", status=JobStatus.SUCCESS, idempotency_key="dep-2")

        job = create_job(db_session, job_type="main_job", idempotency_key="main-1")
        job.dependencies.append(dep1)
        job.dependencies.append(dep2)
        db_session.commit()

        assert resolver.are_dependencies_met(job) is True

    def test_job_with_pending_dependency_not_ready(self, db_session):
        """Test job not ready when dependency is still pending."""
        resolver = DependencyResolver(db_session)

        dep1 = create_job(db_session, job_type="dep1", status=JobStatus.SUCCESS, idempotency_key="dep-success")
        dep2 = create_job(db_session, job_type="dep2", status=JobStatus.RUNNING, idempotency_key="dep-running")

        job = create_job(db_session, job_type="main_job", idempotency_key="main-2")
        job.dependencies.append(dep1)
        job.dependencies.append(dep2)
        db_session.commit()

        assert resolver.are_dependencies_met(job) is False

    def test_job_with_failed_dependency_not_ready(self, db_session):
        """Test job not ready when dependency failed."""
        resolver = DependencyResolver(db_session)

        dep1 = create_job(db_session, job_type="dep1", status=JobStatus.SUCCESS, idempotency_key="dep-ok")
        dep2 = create_job(db_session, job_type="dep2", status=JobStatus.FAILED, idempotency_key="dep-failed")

        job = create_job(db_session, job_type="main_job", idempotency_key="main-3")
        job.dependencies.append(dep1)
        job.dependencies.append(dep2)
        db_session.commit()

        assert resolver.are_dependencies_met(job) is False

    def test_get_ready_jobs_returns_jobs_with_met_dependencies(self, db_session):
        """Test get_ready_jobs returns only jobs ready to execute."""
        resolver = DependencyResolver(db_session)

        # Create dependency jobs
        dep_success = create_job(db_session, job_type="dep", status=JobStatus.SUCCESS, idempotency_key="dep-s")
        dep_running = create_job(db_session, job_type="dep", status=JobStatus.RUNNING, idempotency_key="dep-r")

        # Job 1: No dependencies (ready)
        job1 = create_job(db_session, job_type="job1", status=JobStatus.PENDING, idempotency_key="j1")

        # Job 2: Success dependency (ready)
        job2 = create_job(db_session, job_type="job2", status=JobStatus.PENDING, idempotency_key="j2")
        job2.dependencies.append(dep_success)

        # Job 3: Running dependency (not ready)
        job3 = create_job(db_session, job_type="job3", status=JobStatus.PENDING, idempotency_key="j3")
        job3.dependencies.append(dep_running)

        # Job 4: Already running (not ready)
        job4 = create_job(db_session, job_type="job4", status=JobStatus.RUNNING, idempotency_key="j4")

        db_session.commit()

        ready_jobs = resolver.get_ready_jobs()

        assert len(ready_jobs) == 2
        assert job1 in ready_jobs
        assert job2 in ready_jobs
        assert job3 not in ready_jobs
        assert job4 not in ready_jobs

    def test_has_failed_dependencies(self, db_session):
        """Test checking if job has failed dependencies."""
        resolver = DependencyResolver(db_session)

        dep_ok = create_job(db_session, job_type="dep", status=JobStatus.SUCCESS, idempotency_key="dep-ok-1")
        dep_failed = create_job(db_session, job_type="dep", status=JobStatus.DEAD, idempotency_key="dep-dead")

        job = create_job(db_session, job_type="main", idempotency_key="main-4")
        job.dependencies.append(dep_ok)
        job.dependencies.append(dep_failed)
        db_session.commit()

        assert resolver.has_failed_dependencies(job) is True

    def test_no_failed_dependencies(self, db_session):
        """Test job with no failed dependencies."""
        resolver = DependencyResolver(db_session)

        dep1 = create_job(db_session, job_type="dep", status=JobStatus.SUCCESS, idempotency_key="dep-ok-2")
        dep2 = create_job(db_session, job_type="dep", status=JobStatus.RUNNING, idempotency_key="dep-run")

        job = create_job(db_session, job_type="main", idempotency_key="main-5")
        job.dependencies.append(dep1)
        job.dependencies.append(dep2)
        db_session.commit()

        assert resolver.has_failed_dependencies(job) is False
