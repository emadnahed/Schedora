"""Integration tests for Worker repository."""
import pytest
from datetime import datetime, timedelta, timezone
from schedora.core.enums import WorkerStatus


@pytest.mark.integration
class TestWorkerRepository:
    """Integration tests for WorkerRepository CRUD operations."""

    def test_create_worker(self, db_session):
        """Test creating a worker."""
        from schedora.repositories.worker_repository import WorkerRepository

        repo = WorkerRepository(db_session)

        worker = repo.create(
            worker_id="test-worker-1",
            hostname="test-host",
            pid=12345,
            version="0.1.0",
        )

        assert worker.worker_id == "test-worker-1"
        assert worker.hostname == "test-host"
        assert worker.pid == 12345
        assert worker.version == "0.1.0"
        assert worker.status == WorkerStatus.STARTING

    def test_get_by_id(self, db_session):
        """Test getting worker by ID."""
        from schedora.repositories.worker_repository import WorkerRepository

        repo = WorkerRepository(db_session)

        # Create worker
        created = repo.create(
            worker_id="test-worker-2",
            hostname="test-host",
            pid=12345,
            version="0.1.0",
        )

        # Get by ID
        worker = repo.get_by_id("test-worker-2")

        assert worker is not None
        assert worker.worker_id == created.worker_id
        assert worker.hostname == created.hostname

    def test_get_by_id_not_found(self, db_session):
        """Test getting non-existent worker returns None."""
        from schedora.repositories.worker_repository import WorkerRepository

        repo = WorkerRepository(db_session)

        worker = repo.get_by_id("non-existent-worker")

        assert worker is None

    def test_update_worker(self, db_session):
        """Test updating worker fields."""
        from schedora.repositories.worker_repository import WorkerRepository

        repo = WorkerRepository(db_session)

        # Create worker
        worker = repo.create(
            worker_id="test-worker-3",
            hostname="test-host",
            pid=12345,
            version="0.1.0",
        )

        # Update worker
        updated = repo.update(
            worker_id="test-worker-3",
            status=WorkerStatus.ACTIVE,
            cpu_percent=45.5,
            memory_percent=62.3,
        )

        assert updated.status == WorkerStatus.ACTIVE
        assert updated.cpu_percent == 45.5
        assert updated.memory_percent == 62.3

    def test_get_all_active(self, db_session):
        """Test getting all active workers."""
        from schedora.repositories.worker_repository import WorkerRepository

        repo = WorkerRepository(db_session)

        # Create active workers
        repo.create(worker_id="active-1", hostname="host1", pid=1, version="0.1.0")
        repo.update("active-1", status=WorkerStatus.ACTIVE)

        repo.create(worker_id="active-2", hostname="host2", pid=2, version="0.1.0")
        repo.update("active-2", status=WorkerStatus.ACTIVE)

        # Create stopped worker
        repo.create(worker_id="stopped-1", hostname="host3", pid=3, version="0.1.0")
        repo.update("stopped-1", status=WorkerStatus.STOPPED)

        # Get all active
        active_workers = repo.get_all_active()

        assert len(active_workers) >= 2
        worker_ids = [w.worker_id for w in active_workers]
        assert "active-1" in worker_ids
        assert "active-2" in worker_ids
        assert "stopped-1" not in worker_ids

    def test_get_all_stale(self, db_session):
        """Test getting all stale workers."""
        from schedora.repositories.worker_repository import WorkerRepository

        repo = WorkerRepository(db_session)

        # Create worker with old heartbeat (stale)
        stale_worker = repo.create(
            worker_id="stale-1",
            hostname="host1",
            pid=1,
            version="0.1.0",
        )
        old_heartbeat = datetime.now(timezone.utc) - timedelta(minutes=5)
        repo.update("stale-1", last_heartbeat_at=old_heartbeat, status=WorkerStatus.ACTIVE)

        # Create worker with recent heartbeat (not stale)
        recent_worker = repo.create(
            worker_id="recent-1",
            hostname="host2",
            pid=2,
            version="0.1.0",
        )
        recent_heartbeat = datetime.now(timezone.utc) - timedelta(seconds=10)
        repo.update("recent-1", last_heartbeat_at=recent_heartbeat, status=WorkerStatus.ACTIVE)

        # Get stale workers (with 90 second timeout)
        stale_workers = repo.get_all_stale(heartbeat_timeout_seconds=90)

        worker_ids = [w.worker_id for w in stale_workers]
        assert "stale-1" in worker_ids
        assert "recent-1" not in worker_ids

    def test_increment_current_jobs(self, db_session):
        """Test incrementing worker's current job count."""
        from schedora.repositories.worker_repository import WorkerRepository

        repo = WorkerRepository(db_session)

        worker = repo.create(
            worker_id="test-worker-4",
            hostname="test-host",
            pid=12345,
            version="0.1.0",
        )

        assert worker.current_job_count == 0

        # Increment
        updated = repo.increment_current_jobs("test-worker-4")

        assert updated.current_job_count == 1

        # Increment again
        updated = repo.increment_current_jobs("test-worker-4")

        assert updated.current_job_count == 2

    def test_decrement_current_jobs(self, db_session):
        """Test decrementing worker's current job count."""
        from schedora.repositories.worker_repository import WorkerRepository

        repo = WorkerRepository(db_session)

        worker = repo.create(
            worker_id="test-worker-5",
            hostname="test-host",
            pid=12345,
            version="0.1.0",
        )

        # Set initial count
        repo.update("test-worker-5", current_job_count=3)

        # Decrement
        updated = repo.decrement_current_jobs("test-worker-5")

        assert updated.current_job_count == 2

        # Decrement again
        updated = repo.decrement_current_jobs("test-worker-5")

        assert updated.current_job_count == 1

    def test_decrement_current_jobs_minimum_zero(self, db_session):
        """Test decrementing job count doesn't go below zero."""
        from schedora.repositories.worker_repository import WorkerRepository

        repo = WorkerRepository(db_session)

        worker = repo.create(
            worker_id="test-worker-6",
            hostname="test-host",
            pid=12345,
            version="0.1.0",
        )

        assert worker.current_job_count == 0

        # Try to decrement when already zero
        updated = repo.decrement_current_jobs("test-worker-6")

        assert updated.current_job_count == 0

    def test_delete_old_stopped_workers(self, db_session):
        """Test deleting old stopped workers."""
        from schedora.repositories.worker_repository import WorkerRepository

        repo = WorkerRepository(db_session)

        # Create old stopped worker
        old_worker = repo.create(
            worker_id="old-stopped",
            hostname="host1",
            pid=1,
            version="0.1.0",
        )
        old_time = datetime.now(timezone.utc) - timedelta(hours=2)
        repo.update("old-stopped", status=WorkerStatus.STOPPED, stopped_at=old_time)

        # Create recent stopped worker
        recent_worker = repo.create(
            worker_id="recent-stopped",
            hostname="host2",
            pid=2,
            version="0.1.0",
        )
        recent_time = datetime.now(timezone.utc) - timedelta(minutes=10)
        repo.update("recent-stopped", status=WorkerStatus.STOPPED, stopped_at=recent_time)

        # Create active worker
        active_worker = repo.create(
            worker_id="active-worker",
            hostname="host3",
            pid=3,
            version="0.1.0",
        )
        repo.update("active-worker", status=WorkerStatus.ACTIVE)

        # Delete old stopped workers (older than 1 hour)
        deleted_count = repo.delete_old_stopped_workers(cleanup_after_seconds=3600)

        assert deleted_count == 1

        # Verify old worker is deleted
        assert repo.get_by_id("old-stopped") is None

        # Verify recent stopped worker still exists
        assert repo.get_by_id("recent-stopped") is not None

        # Verify active worker still exists
        assert repo.get_by_id("active-worker") is not None

    def test_get_all(self, db_session):
        """Test getting all workers regardless of status."""
        from schedora.repositories.worker_repository import WorkerRepository

        repo = WorkerRepository(db_session)

        # Create workers with different statuses
        repo.create(worker_id="w1", hostname="host1", pid=1, version="0.1.0")
        repo.update("w1", status=WorkerStatus.ACTIVE)

        repo.create(worker_id="w2", hostname="host2", pid=2, version="0.1.0")
        repo.update("w2", status=WorkerStatus.STOPPED)

        repo.create(worker_id="w3", hostname="host3", pid=3, version="0.1.0")
        repo.update("w3", status=WorkerStatus.STALE)

        # Get all workers
        all_workers = repo.get_all()

        assert len(all_workers) >= 3
        worker_ids = [w.worker_id for w in all_workers]
        assert "w1" in worker_ids
        assert "w2" in worker_ids
        assert "w3" in worker_ids

    def test_increment_job_metrics(self, db_session):
        """Test incrementing job processing metrics."""
        from schedora.repositories.worker_repository import WorkerRepository

        repo = WorkerRepository(db_session)

        worker = repo.create(
            worker_id="test-worker-7",
            hostname="test-host",
            pid=12345,
            version="0.1.0",
        )

        assert worker.total_jobs_processed == 0
        assert worker.total_jobs_succeeded == 0
        assert worker.total_jobs_failed == 0

        # Update metrics manually
        repo.update(
            "test-worker-7",
            total_jobs_processed=10,
            total_jobs_succeeded=8,
            total_jobs_failed=2,
        )

        updated = repo.get_by_id("test-worker-7")

        assert updated.total_jobs_processed == 10
        assert updated.total_jobs_succeeded == 8
        assert updated.total_jobs_failed == 2
