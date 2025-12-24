"""Async worker for concurrent job execution."""
import asyncio
import logging
from typing import Optional, Set
from sqlalchemy.orm import Session
from schedora.worker.handler_registry import HandlerRegistry
from schedora.worker.job_executor import JobExecutor
from schedora.worker.database_adapter import DatabaseAdapter
from schedora.services.scheduler import Scheduler
from schedora.services.job_service import JobService
from schedora.models.job import Job

logger = logging.getLogger(__name__)


class AsyncWorker:
    """
    Async worker that polls for jobs and executes them concurrently.

    Uses asyncio semaphore for concurrency control and adaptive
    polling with backoff.
    """

    def __init__(
        self,
        worker_id: str,
        db_session: Session,
        handler_registry: HandlerRegistry,
        max_concurrent_jobs: int = 10,
        poll_interval: float = 1.0,
        use_test_session: bool = False,
    ):
        """
        Initialize async worker.

        Args:
            worker_id: Unique worker identifier
            db_session: Database session
            handler_registry: Handler registry
            max_concurrent_jobs: Maximum concurrent jobs
            poll_interval: Polling interval in seconds
            use_test_session: If True, reuse db_session for all operations (testing only)
        """
        self.worker_id = worker_id
        self.db_session = db_session
        self.handler_registry = handler_registry
        self.max_concurrent_jobs = max_concurrent_jobs
        self.poll_interval = poll_interval
        self.use_test_session = use_test_session

        # Concurrency control
        self._semaphore = asyncio.Semaphore(max_concurrent_jobs)
        self._running_tasks: Set[asyncio.Task] = set()

        # Services
        self.scheduler = Scheduler(db_session, worker_id=worker_id)
        self.job_service = JobService(db_session)
        self.adapter = DatabaseAdapter(job_service=self.job_service)
        self.executor = JobExecutor(
            handler_registry,
            self.adapter,
            self.job_service,
            use_test_session=use_test_session,
        )

        # State
        self.is_running = False
        self._stop_event = asyncio.Event()

        # Metrics
        self.jobs_processed = 0
        self.jobs_succeeded = 0
        self.jobs_failed = 0

    async def start(self):
        """
        Start the worker polling loop.

        Continuously polls for jobs and executes them until stopped.
        """
        self.is_running = True
        logger.info(f"Worker {self.worker_id} starting...")

        try:
            await self._poll_loop()
        finally:
            self.is_running = False
            logger.info(f"Worker {self.worker_id} stopped")

    async def stop(self, timeout: float = 30.0):
        """
        Stop the worker gracefully.

        Args:
            timeout: Maximum time to wait for running jobs
        """
        logger.info(f"Worker {self.worker_id} stopping...")
        self._stop_event.set()

        # Wait for running tasks to complete
        if self._running_tasks:
            logger.info(f"Waiting for {len(self._running_tasks)} running jobs...")
            try:
                await asyncio.wait_for(
                    asyncio.gather(*self._running_tasks, return_exceptions=True),
                    timeout=timeout,
                )
            except asyncio.TimeoutError:
                logger.warning(f"Timeout waiting for jobs, cancelling...")
                for task in self._running_tasks:
                    task.cancel()

    async def _poll_loop(self):
        """
        Main polling loop.

        Polls for jobs at regular intervals until stopped.
        """
        while not self._stop_event.is_set():
            try:
                # Claim job
                job = await self._claim_job()

                if job:
                    if self.use_test_session:
                        # Test mode: Execute synchronously in same thread
                        await self._execute_job_with_semaphore(job)
                    else:
                        # Production: Job already expunged in claim_sync
                        # Execute job with semaphore in background
                        task = asyncio.create_task(
                            self._execute_job_with_semaphore(job)
                        )
                        self._running_tasks.add(task)
                        task.add_done_callback(self._running_tasks.discard)
                else:
                    # No job available, wait before polling again
                    await asyncio.sleep(self.poll_interval)

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in poll loop: {e}", exc_info=True)
                await asyncio.sleep(self.poll_interval)

    async def _claim_job(self) -> Optional[Job]:
        """
        Claim a job from the scheduler.

        Returns:
            Optional[Job]: Claimed job or None
        """
        if self.use_test_session:
            # For testing: call directly in same thread
            try:
                return self.scheduler.claim_job()
            except Exception as e:
                logger.error(f"Error claiming job: {e}", exc_info=True)
                return None
        else:
            # Production: create fresh session for thread safety
            def claim_sync():
                from schedora.core.database import SessionLocal
                from schedora.services.scheduler import Scheduler
                session = SessionLocal()
                try:
                    scheduler = Scheduler(session, worker_id=self.worker_id)
                    job = scheduler.claim_job()
                    # Force load all attributes before expunging
                    if job:
                        _ = (job.job_id, job.type, job.payload, job.timeout_seconds,
                             job.status, job.max_retries, job.retry_count)
                        session.expunge(job)
                    return job
                except Exception as e:
                    logger.error(f"Error in claim_sync: {e}", exc_info=True)
                    return None
                finally:
                    session.close()

            try:
                return await asyncio.to_thread(claim_sync)
            except Exception as e:
                logger.error(f"Error claiming job: {e}", exc_info=True)
                return None

    async def _execute_job_with_semaphore(self, job: Job):
        """
        Execute job with concurrency control.

        Args:
            job: Job to execute
        """
        async with self._semaphore:
            try:
                # Extract job info before async execution to avoid session issues
                job_id = job.job_id
                job_type = job.type

                logger.info(f"Executing job {job_id} (type: {job_type})")
                result = await self.executor.execute(job)

                # Update metrics
                self.jobs_processed += 1
                if result.success:
                    self.jobs_succeeded += 1
                    logger.info(f"Job {job_id} succeeded")
                else:
                    self.jobs_failed += 1
                    logger.error(f"Job {job_id} failed: {result.error_message}")

            except Exception as e:
                self.jobs_failed += 1
                logger.error(f"Unexpected error executing job: {e}", exc_info=True)
