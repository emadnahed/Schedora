"""Background task manager for periodic operations."""
import asyncio
import logging
from typing import Optional
from sqlalchemy.orm import Session
from redis import Redis
from schedora.config import get_settings
from schedora.services.heartbeat_service import HeartbeatService

settings = get_settings()
logger = logging.getLogger(__name__)


class BackgroundTaskManager:
    """
    Manages background tasks for worker monitoring and cleanup.

    Runs periodic tasks like:
    - Stale worker detection
    - Worker cleanup
    """

    def __init__(self, db: Session, redis: Redis):
        """
        Initialize background task manager.

        Args:
            db: Database session
            redis: Redis client
        """
        self.db = db
        self.redis = redis
        self.heartbeat_service = HeartbeatService(db, redis)
        self.is_running = False
        self._tasks: list[asyncio.Task] = []
        self._stop_event = asyncio.Event()

    async def start(self) -> None:
        """Start all background tasks."""
        if self.is_running:
            logger.warning("Background tasks already running")
            return

        self.is_running = True
        logger.info("Starting background tasks...")

        # Start stale worker detector
        task = asyncio.create_task(self._stale_worker_detector())
        self._tasks.append(task)

        # Start worker cleanup
        task = asyncio.create_task(self._worker_cleanup_task())
        self._tasks.append(task)

        logger.info(f"Started {len(self._tasks)} background tasks")

    async def stop(self, timeout: float = 10.0) -> None:
        """
        Stop all background tasks gracefully.

        Args:
            timeout: Maximum time to wait for tasks to complete
        """
        if not self.is_running:
            return

        logger.info("Stopping background tasks...")
        self._stop_event.set()

        # Wait for tasks with timeout
        try:
            await asyncio.wait_for(
                asyncio.gather(*self._tasks, return_exceptions=True),
                timeout=timeout,
            )
        except asyncio.TimeoutError:
            logger.warning("Background tasks did not stop in time, cancelling...")
            for task in self._tasks:
                task.cancel()

        self.is_running = False
        self._tasks.clear()
        logger.info("Background tasks stopped")

    async def _stale_worker_detector(self) -> None:
        """
        Periodically detect and handle stale workers.

        Runs every WORKER_STALE_CHECK_INTERVAL seconds.
        """
        interval = settings.WORKER_STALE_CHECK_INTERVAL
        logger.info(f"Stale worker detector started (interval: {interval}s)")

        while not self._stop_event.is_set():
            try:
                # Detect stale workers
                stale_workers = await asyncio.to_thread(
                    self.heartbeat_service.detect_stale_workers
                )

                if stale_workers:
                    logger.warning(f"Detected {len(stale_workers)} stale workers")

                    # Handle each stale worker
                    for worker in stale_workers:
                        try:
                            await asyncio.to_thread(
                                self.heartbeat_service.handle_stale_worker,
                                worker.worker_id,
                            )
                            logger.info(
                                f"Handled stale worker: {worker.worker_id}, "
                                f"reassigned jobs"
                            )
                        except Exception as e:
                            logger.error(
                                f"Error handling stale worker {worker.worker_id}: {e}",
                                exc_info=True,
                            )

            except Exception as e:
                logger.error(f"Error in stale worker detector: {e}", exc_info=True)

            # Wait for next check
            try:
                await asyncio.wait_for(
                    self._stop_event.wait(),
                    timeout=interval,
                )
            except asyncio.TimeoutError:
                pass  # Normal timeout, continue loop

    async def _worker_cleanup_task(self) -> None:
        """
        Periodically clean up old stopped workers.

        Runs at configured interval (default: 1 hour).
        """
        interval = settings.WORKER_CLEANUP_INTERVAL
        logger.info(f"Worker cleanup task started (interval: {interval}s)")

        while not self._stop_event.is_set():
            try:
                # Cleanup old workers
                deleted_count = await asyncio.to_thread(
                    self.heartbeat_service.cleanup_old_workers
                )

                if deleted_count > 0:
                    logger.info(f"Cleaned up {deleted_count} old workers")

            except Exception as e:
                logger.error(f"Error in worker cleanup task: {e}", exc_info=True)

            # Wait for next cleanup
            try:
                await asyncio.wait_for(
                    self._stop_event.wait(),
                    timeout=interval,
                )
            except asyncio.TimeoutError:
                pass  # Normal timeout, continue loop
