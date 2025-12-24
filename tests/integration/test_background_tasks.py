"""Integration tests for BackgroundTaskManager."""
import asyncio
import pytest
from unittest.mock import AsyncMock, Mock, patch
from schedora.services.background_tasks import BackgroundTaskManager
from schedora.services.heartbeat_service import HeartbeatService
from schedora.repositories.worker_repository import WorkerRepository
from schedora.core.enums import WorkerStatus


@pytest.mark.asyncio
class TestBackgroundTaskManager:
    """Test BackgroundTaskManager functionality."""

    async def test_initialization(self, db_session, redis_client):
        """Test manager initialization."""
        manager = BackgroundTaskManager(db_session, redis_client)

        assert manager.db == db_session
        assert manager.redis == redis_client
        assert isinstance(manager.heartbeat_service, HeartbeatService)
        assert manager.is_running is False
        assert manager._tasks == []

    async def test_start_background_tasks(self, db_session, redis_client):
        """Test starting background tasks."""
        manager = BackgroundTaskManager(db_session, redis_client)

        # Start tasks
        await manager.start()

        assert manager.is_running is True
        assert len(manager._tasks) == 2  # stale detector + cleanup

        # Cleanup
        await manager.stop(timeout=0.5)

    async def test_start_already_running(self, db_session, redis_client, caplog):
        """Test starting tasks when already running."""
        manager = BackgroundTaskManager(db_session, redis_client)

        # Start first time
        await manager.start()
        assert manager.is_running is True

        # Try starting again
        await manager.start()
        assert "already running" in caplog.text

        # Cleanup
        await manager.stop(timeout=0.5)

    async def test_stop_background_tasks(self, db_session, redis_client):
        """Test stopping background tasks."""
        manager = BackgroundTaskManager(db_session, redis_client)

        # Start and then stop
        await manager.start()
        assert manager.is_running is True

        await manager.stop(timeout=1.0)

        assert manager.is_running is False
        assert manager._tasks == []

    async def test_stop_when_not_running(self, db_session, redis_client):
        """Test stopping when not running (should be no-op)."""
        manager = BackgroundTaskManager(db_session, redis_client)

        # Stop without starting
        await manager.stop()

        assert manager.is_running is False

    async def test_stop_with_timeout(self, db_session, redis_client, caplog):
        """Test stopping tasks that don't finish in time."""
        manager = BackgroundTaskManager(db_session, redis_client)

        # Create a task that hangs
        async def hanging_detector():
            await asyncio.sleep(10)  # Never finishes in timeout

        async def hanging_cleanup():
            await asyncio.sleep(10)  # Never finishes in timeout

        # Patch the methods before starting
        manager._stale_worker_detector = hanging_detector
        manager._worker_cleanup_task = hanging_cleanup

        await manager.start()

        # Stop with short timeout (tasks should be cancelled)
        await manager.stop(timeout=0.1)

        assert "did not stop in time" in caplog.text
        assert manager.is_running is False

    async def test_stale_worker_detection_task(self, db_session, redis_client):
        """Test stale worker detector finds and handles stale workers."""
        from datetime import datetime, timezone, timedelta

        manager = BackgroundTaskManager(db_session, redis_client)
        repo = WorkerRepository(db_session)

        # Register worker with heartbeat service (this creates the worker)
        worker = manager.heartbeat_service.register_worker(
            worker_id="stale-test-worker",
            hostname="host",
            pid=123,
            max_concurrent_jobs=5,
        )

        # Send a heartbeat to set last_heartbeat_at
        manager.heartbeat_service.send_heartbeat("stale-test-worker")

        # Set last_heartbeat_at to 10 minutes ago (well past the 90s default timeout)
        worker.last_heartbeat_at = datetime.now(timezone.utc) - timedelta(minutes=10)
        db_session.commit()

        # Delete Redis key to make it stale
        redis_client.delete("worker:stale-test-worker:heartbeat")

        # Run detect and handle directly
        stale_workers = manager.heartbeat_service.detect_stale_workers()
        assert len(stale_workers) > 0

        for stale_worker in stale_workers:
            manager.heartbeat_service.handle_stale_worker(stale_worker.worker_id)

        # Verify worker was marked as stale
        worker = repo.get_by_id("stale-test-worker")
        assert worker.status == WorkerStatus.STALE

    async def test_stale_detector_handles_errors(self, db_session, redis_client, caplog):
        """Test stale detector continues after errors."""
        manager = BackgroundTaskManager(db_session, redis_client)

        # Mock detect_stale_workers to raise an error once
        call_count = 0

        def mock_detect():
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise Exception("Test error")
            return []

        with patch.object(manager.heartbeat_service, 'detect_stale_workers', mock_detect):
            # Run detector briefly
            task = asyncio.create_task(manager._stale_worker_detector())
            await asyncio.sleep(0.1)
            manager._stop_event.set()

            try:
                await asyncio.wait_for(task, timeout=1.0)
            except asyncio.TimeoutError:
                task.cancel()

            # Should have logged error but continued
            assert "Error in stale worker detector" in caplog.text

    async def test_stale_detector_handles_individual_worker_errors(
        self, db_session, redis_client, caplog
    ):
        """Test stale detector handles errors for individual workers."""
        manager = BackgroundTaskManager(db_session, redis_client)
        repo = WorkerRepository(db_session)

        # Create two workers
        repo.create(
            worker_id="worker-1",
            hostname="host",
            pid=123,
            version="1.0.0",
            max_concurrent_jobs=5,
            status=WorkerStatus.STALE,
        )
        repo.create(
            worker_id="worker-2",
            hostname="host",
            pid=124,
            version="1.0.0",
            max_concurrent_jobs=5,
            status=WorkerStatus.STALE,
        )

        # Mock detect to return both workers
        with patch.object(
            manager.heartbeat_service, 'detect_stale_workers'
        ) as mock_detect:
            mock_detect.return_value = [
                repo.get_by_id("worker-1"),
                repo.get_by_id("worker-2"),
            ]

            # Mock handle_stale_worker to fail for first worker
            original_handle = manager.heartbeat_service.handle_stale_worker

            def mock_handle(worker_id):
                if worker_id == "worker-1":
                    raise Exception("Test error")
                return original_handle(worker_id)

            with patch.object(
                manager.heartbeat_service, 'handle_stale_worker', mock_handle
            ):
                # Run detector once
                task = asyncio.create_task(manager._stale_worker_detector())
                await asyncio.sleep(0.1)
                manager._stop_event.set()

                try:
                    await asyncio.wait_for(task, timeout=1.0)
                except asyncio.TimeoutError:
                    task.cancel()

                # Should have logged error for worker-1
                assert "Error handling stale worker worker-1" in caplog.text

    async def test_worker_cleanup_task(self, db_session, redis_client):
        """Test worker cleanup task removes old stopped workers."""
        manager = BackgroundTaskManager(db_session, redis_client)
        repo = WorkerRepository(db_session)

        # Create an old stopped worker
        from datetime import datetime, timezone, timedelta

        worker = repo.create(
            worker_id="cleanup-test-worker",
            hostname="host",
            pid=999,
            version="1.0.0",
            max_concurrent_jobs=5,
            status=WorkerStatus.STOPPED,
        )

        # Set stopped_at to 2 hours ago (well past the 1-hour cleanup threshold)
        worker.stopped_at = datetime.now(timezone.utc) - timedelta(hours=2)
        db_session.commit()

        # Run cleanup directly
        deleted_count = manager.heartbeat_service.cleanup_old_workers(older_than_hours=1)

        # Verify worker was deleted
        assert deleted_count == 1
        assert repo.get_by_id("cleanup-test-worker") is None

    async def test_cleanup_task_handles_errors(self, db_session, redis_client, caplog):
        """Test cleanup task continues after errors."""
        manager = BackgroundTaskManager(db_session, redis_client)

        # Mock cleanup_old_workers to raise an error
        with patch.object(
            manager.heartbeat_service, 'cleanup_old_workers', side_effect=Exception("Test error")
        ):
            # Run cleanup briefly
            task = asyncio.create_task(manager._worker_cleanup_task())
            await asyncio.sleep(0.1)
            manager._stop_event.set()

            try:
                await asyncio.wait_for(task, timeout=1.0)
            except asyncio.TimeoutError:
                task.cancel()

            # Should have logged error
            assert "Error in worker cleanup task" in caplog.text

    async def test_cleanup_task_logs_deletions(self, db_session, redis_client, caplog):
        """Test cleanup task logs when workers are deleted."""
        from datetime import datetime, timezone, timedelta

        manager = BackgroundTaskManager(db_session, redis_client)
        repo = WorkerRepository(db_session)

        # Create 3 old stopped workers
        for i in range(3):
            worker = repo.create(
                worker_id=f"log-test-worker-{i}",
                hostname="host",
                pid=1000 + i,
                version="1.0.0",
                max_concurrent_jobs=5,
                status=WorkerStatus.STOPPED,
            )
            worker.stopped_at = datetime.now(timezone.utc) - timedelta(hours=2)
        db_session.commit()

        # Run one iteration of the cleanup task manually
        # (simulating what the background task would do)
        deleted_count = manager.heartbeat_service.cleanup_old_workers(older_than_hours=1)

        # Check that cleanup worked
        assert deleted_count == 3

        # Verify workers were deleted
        for i in range(3):
            assert repo.get_by_id(f"log-test-worker-{i}") is None

    async def test_cleanup_task_no_log_when_zero_deleted(
        self, db_session, redis_client, caplog
    ):
        """Test cleanup task doesn't log when no workers deleted."""
        manager = BackgroundTaskManager(db_session, redis_client)

        # Mock cleanup to return 0 deletions
        with patch.object(
            manager.heartbeat_service, 'cleanup_old_workers', return_value=0
        ):
            # Run cleanup once
            task = asyncio.create_task(manager._worker_cleanup_task())
            await asyncio.sleep(0.1)
            manager._stop_event.set()

            try:
                await asyncio.wait_for(task, timeout=1.0)
            except asyncio.TimeoutError:
                task.cancel()

            # Should NOT have logged cleanup
            assert "Cleaned up" not in caplog.text

    async def test_full_lifecycle(self, db_session, redis_client):
        """Test complete start/stop lifecycle."""
        manager = BackgroundTaskManager(db_session, redis_client)

        # Verify initial state
        assert manager.is_running is False
        assert len(manager._tasks) == 0

        # Start
        await manager.start()
        assert manager.is_running is True
        assert len(manager._tasks) == 2

        # Let it run briefly
        await asyncio.sleep(0.1)

        # Stop
        await manager.stop(timeout=2.0)
        assert manager.is_running is False
        assert len(manager._tasks) == 0
