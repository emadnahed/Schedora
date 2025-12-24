"""Integration tests for Worker model."""
import pytest
import os
from datetime import datetime, timezone
from sqlalchemy.exc import IntegrityError
from schedora.core.enums import WorkerStatus


@pytest.mark.integration
class TestWorkerModel:
    """Integration tests for Worker database model."""

    def test_create_worker_with_minimal_fields(self, db_session):
        """Test creating a worker with only required fields."""
        from schedora.models.worker import Worker

        worker = Worker(
            worker_id="test-worker-1",
            hostname="test-host",
            pid=12345,
            version="0.1.0",
        )

        db_session.add(worker)
        db_session.commit()

        # Verify worker was created
        assert worker.worker_id == "test-worker-1"
        assert worker.hostname == "test-host"
        assert worker.pid == 12345
        assert worker.version == "0.1.0"
        assert worker.status == WorkerStatus.STARTING
        assert worker.current_job_count == 0
        assert worker.max_concurrent_jobs == 10  # default
        assert worker.created_at is not None
        assert worker.updated_at is not None

    def test_worker_status_transitions(self, db_session):
        """Test worker status can transition through lifecycle."""
        from schedora.models.worker import Worker

        worker = Worker(
            worker_id="test-worker-2",
            hostname="test-host",
            pid=12345,
            version="0.1.0",
            status=WorkerStatus.STARTING,
        )

        db_session.add(worker)
        db_session.commit()

        # STARTING → ACTIVE
        worker.status = WorkerStatus.ACTIVE
        db_session.commit()
        assert worker.status == WorkerStatus.ACTIVE

        # ACTIVE → STALE (detected by heartbeat timeout)
        worker.status = WorkerStatus.STALE
        db_session.commit()
        assert worker.status == WorkerStatus.STALE

        # STALE → ACTIVE (recovered)
        worker.status = WorkerStatus.ACTIVE
        db_session.commit()
        assert worker.status == WorkerStatus.ACTIVE

        # ACTIVE → STOPPING
        worker.status = WorkerStatus.STOPPING
        db_session.commit()
        assert worker.status == WorkerStatus.STOPPING

        # STOPPING → STOPPED
        worker.status = WorkerStatus.STOPPED
        db_session.commit()
        assert worker.status == WorkerStatus.STOPPED

    def test_heartbeat_timestamp_updates(self, db_session):
        """Test heartbeat timestamp can be updated."""
        from schedora.models.worker import Worker

        worker = Worker(
            worker_id="test-worker-3",
            hostname="test-host",
            pid=12345,
            version="0.1.0",
        )

        db_session.add(worker)
        db_session.commit()

        # Initial heartbeat should be None
        assert worker.last_heartbeat_at is None

        # Update heartbeat
        heartbeat_time = datetime.now(timezone.utc)
        worker.last_heartbeat_at = heartbeat_time
        db_session.commit()

        assert worker.last_heartbeat_at == heartbeat_time

        # Update again
        new_heartbeat = datetime.now(timezone.utc)
        worker.last_heartbeat_at = new_heartbeat
        db_session.commit()

        assert worker.last_heartbeat_at == new_heartbeat
        assert worker.last_heartbeat_at > heartbeat_time

    def test_job_count_constraints(self, db_session):
        """Test job count constraints are enforced."""
        from schedora.models.worker import Worker

        worker = Worker(
            worker_id="test-worker-4",
            hostname="test-host",
            pid=12345,
            version="0.1.0",
            max_concurrent_jobs=5,
            current_job_count=0,
        )

        db_session.add(worker)
        db_session.commit()

        # Increment job count
        worker.current_job_count = 3
        db_session.commit()
        assert worker.current_job_count == 3

        # Set to max
        worker.current_job_count = 5
        db_session.commit()
        assert worker.current_job_count == 5

        # Exceeding max should fail
        worker.current_job_count = 6
        with pytest.raises(IntegrityError):
            db_session.commit()

        db_session.rollback()

        # Negative count should fail
        worker.current_job_count = -1
        with pytest.raises(IntegrityError):
            db_session.commit()

        db_session.rollback()

    def test_metrics_tracking(self, db_session):
        """Test worker metrics can be tracked."""
        from schedora.models.worker import Worker

        worker = Worker(
            worker_id="test-worker-5",
            hostname="test-host",
            pid=12345,
            version="0.1.0",
        )

        db_session.add(worker)
        db_session.commit()

        # Initial metrics should be 0
        assert worker.total_jobs_processed == 0
        assert worker.total_jobs_succeeded == 0
        assert worker.total_jobs_failed == 0

        # Update metrics
        worker.total_jobs_processed = 10
        worker.total_jobs_succeeded = 8
        worker.total_jobs_failed = 2
        db_session.commit()

        assert worker.total_jobs_processed == 10
        assert worker.total_jobs_succeeded == 8
        assert worker.total_jobs_failed == 2

    def test_worker_lifecycle_timestamps(self, db_session):
        """Test worker lifecycle timestamps."""
        from schedora.models.worker import Worker

        worker = Worker(
            worker_id="test-worker-6",
            hostname="test-host",
            pid=12345,
            version="0.1.0",
        )

        db_session.add(worker)
        db_session.commit()

        # Initial timestamps
        assert worker.started_at is None
        assert worker.stopped_at is None

        # Set started_at
        started_time = datetime.now(timezone.utc)
        worker.started_at = started_time
        worker.status = WorkerStatus.ACTIVE
        db_session.commit()

        assert worker.started_at == started_time
        assert worker.stopped_at is None

        # Set stopped_at
        stopped_time = datetime.now(timezone.utc)
        worker.stopped_at = stopped_time
        worker.status = WorkerStatus.STOPPED
        db_session.commit()

        assert worker.stopped_at == stopped_time
        assert worker.stopped_at >= worker.started_at

    def test_worker_system_metrics(self, db_session):
        """Test worker can track system metrics."""
        from schedora.models.worker import Worker

        worker = Worker(
            worker_id="test-worker-7",
            hostname="test-host",
            pid=12345,
            version="0.1.0",
            cpu_percent=45.5,
            memory_percent=62.3,
        )

        db_session.add(worker)
        db_session.commit()

        assert worker.cpu_percent == 45.5
        assert worker.memory_percent == 62.3

        # Update metrics
        worker.cpu_percent = 55.2
        worker.memory_percent = 70.1
        db_session.commit()

        assert worker.cpu_percent == 55.2
        assert worker.memory_percent == 70.1

    def test_worker_capabilities_and_metadata(self, db_session):
        """Test worker can store capabilities and metadata as JSONB."""
        from schedora.models.worker import Worker

        capabilities = {
            "handlers": ["echo", "sleep", "http"],
            "max_memory_mb": 2048,
            "features": ["retry", "timeout"],
        }

        worker_metadata = {
            "environment": "production",
            "region": "us-west-2",
            "tags": ["high-priority", "batch-processing"],
        }

        worker = Worker(
            worker_id="test-worker-8",
            hostname="test-host",
            pid=12345,
            version="0.1.0",
            capabilities=capabilities,
            worker_metadata=worker_metadata,
        )

        db_session.add(worker)
        db_session.commit()

        assert worker.capabilities == capabilities
        assert worker.worker_metadata == worker_metadata

        # Update capabilities (need to reassign for JSONB to detect change)
        updated_capabilities = {
            "handlers": ["echo", "sleep", "http", "fail"],
            "max_memory_mb": 2048,
            "features": ["retry", "timeout"],
        }
        worker.capabilities = updated_capabilities
        db_session.commit()
        db_session.refresh(worker)

        assert "fail" in worker.capabilities["handlers"]

    def test_unique_worker_id_constraint(self, db_session):
        """Test worker_id must be unique."""
        from schedora.models.worker import Worker

        worker1 = Worker(
            worker_id="duplicate-worker",
            hostname="host1",
            pid=12345,
            version="0.1.0",
        )

        db_session.add(worker1)
        db_session.commit()

        # Try to create duplicate
        worker2 = Worker(
            worker_id="duplicate-worker",
            hostname="host2",
            pid=54321,
            version="0.1.0",
        )

        db_session.add(worker2)
        with pytest.raises(IntegrityError):
            db_session.commit()

        db_session.rollback()

    def test_max_concurrent_jobs_constraint(self, db_session):
        """Test max_concurrent_jobs must be positive."""
        from schedora.models.worker import Worker

        worker = Worker(
            worker_id="test-worker-9",
            hostname="test-host",
            pid=12345,
            version="0.1.0",
            max_concurrent_jobs=-1,
        )

        db_session.add(worker)
        with pytest.raises(IntegrityError):
            db_session.commit()

        db_session.rollback()

        # Zero should also fail
        worker.max_concurrent_jobs = 0
        db_session.add(worker)
        with pytest.raises(IntegrityError):
            db_session.commit()

        db_session.rollback()
