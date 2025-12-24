"""Heartbeat service for worker health monitoring."""
from datetime import datetime, timezone, timedelta
from typing import List, Set
from uuid import UUID
from redis import Redis
from sqlalchemy.orm import Session
from schedora.config import get_settings
from schedora.core.enums import WorkerStatus, JobStatus
from schedora.models.worker import Worker
from schedora.repositories.worker_repository import WorkerRepository
from schedora.repositories.job_repository import JobRepository

settings = get_settings()


class HeartbeatService:
    """
    Manages worker heartbeats and health monitoring.

    Uses hybrid approach:
    - DB: Persistence and worker metadata
    - Redis: Fast TTL-based stale detection
    """

    def __init__(self, db: Session, redis: Redis):
        """
        Initialize heartbeat service.

        Args:
            db: Database session
            redis: Redis client
        """
        self.db = db
        self.redis = redis
        self.worker_repo = WorkerRepository(db)
        self.job_repo = JobRepository(db)
        self.heartbeat_timeout = settings.WORKER_HEARTBEAT_TIMEOUT

    def register_worker(
        self,
        worker_id: str,
        hostname: str,
        pid: int,
        max_concurrent_jobs: int,
        version: str = "1.0.0",
        capabilities: dict = None,
        metadata: dict = None,
    ) -> Worker:
        """
        Register a new worker.

        Creates DB record and initializes Redis heartbeat key.

        Args:
            worker_id: Unique worker identifier
            hostname: Worker hostname
            pid: Process ID
            max_concurrent_jobs: Maximum concurrent jobs
            version: Worker version
            capabilities: Optional worker capabilities
            metadata: Optional worker metadata

        Returns:
            Worker: Created worker record
        """
        # Create DB record
        worker = self.worker_repo.create(
            worker_id=worker_id,
            hostname=hostname,
            pid=pid,
            version=version,
            max_concurrent_jobs=max_concurrent_jobs,
            status=WorkerStatus.ACTIVE,
            started_at=datetime.now(timezone.utc),
            capabilities=capabilities or {},
            worker_metadata=metadata or {},
        )

        # Initialize Redis heartbeat with TTL
        heartbeat_key = f"worker:{worker_id}:heartbeat"
        self.redis.setex(
            heartbeat_key,
            self.heartbeat_timeout,
            datetime.now(timezone.utc).isoformat(),
        )

        return worker

    def send_heartbeat(
        self,
        worker_id: str,
        cpu_percent: float = None,
        memory_percent: float = None,
    ) -> None:
        """
        Send heartbeat for a worker.

        Updates Redis TTL and DB timestamp.

        Args:
            worker_id: Worker identifier
            cpu_percent: Optional CPU usage percentage
            memory_percent: Optional memory usage percentage
        """
        now = datetime.now(timezone.utc)

        # Update Redis TTL
        heartbeat_key = f"worker:{worker_id}:heartbeat"
        self.redis.setex(heartbeat_key, self.heartbeat_timeout, now.isoformat())

        # Update DB timestamp and metrics
        worker = self.worker_repo.get_by_id(worker_id)
        if worker:
            worker.last_heartbeat_at = now
            if cpu_percent is not None:
                worker.cpu_percent = cpu_percent
            if memory_percent is not None:
                worker.memory_percent = memory_percent
            self.db.commit()

    def detect_stale_workers(self) -> List[Worker]:
        """
        Detect stale workers based on Redis TTL expiration.

        Returns:
            List[Worker]: List of stale workers
        """
        stale_workers = []

        # Get all active workers
        active_workers = self.worker_repo.get_all_active()

        for worker in active_workers:
            heartbeat_key = f"worker:{worker.worker_id}:heartbeat"

            # Check if Redis key expired
            if not self.redis.exists(heartbeat_key):
                # Mark as stale
                worker.status = WorkerStatus.STALE
                stale_workers.append(worker)

        self.db.commit()
        return stale_workers

    def handle_stale_worker(self, worker_id: str) -> None:
        """
        Handle a stale worker by reassigning its jobs.

        Args:
            worker_id: Worker identifier
        """
        # Get jobs assigned to this worker
        job_ids = self.get_worker_jobs(worker_id)

        # Reassign jobs to PENDING
        for job_id in job_ids:
            job = self.job_repo.get_by_id(job_id)
            if job and job.status == JobStatus.RUNNING:
                job.status = JobStatus.PENDING
                self.db.commit()

        # Clear Redis job assignments
        jobs_key = f"worker:{worker_id}:jobs"
        self.redis.delete(jobs_key)

    def assign_job_to_worker(self, worker_id: str, job_id: UUID) -> None:
        """
        Track job assignment to worker in Redis.

        Args:
            worker_id: Worker identifier
            job_id: Job identifier
        """
        jobs_key = f"worker:{worker_id}:jobs"
        self.redis.sadd(jobs_key, str(job_id))

    def remove_job_from_worker(self, worker_id: str, job_id: UUID) -> None:
        """
        Remove job from worker's assignment in Redis.

        Args:
            worker_id: Worker identifier
            job_id: Job identifier
        """
        jobs_key = f"worker:{worker_id}:jobs"
        self.redis.srem(jobs_key, str(job_id))

    def get_worker_jobs(self, worker_id: str) -> Set[UUID]:
        """
        Get all jobs currently assigned to a worker.

        Args:
            worker_id: Worker identifier

        Returns:
            Set[UUID]: Set of job IDs
        """
        jobs_key = f"worker:{worker_id}:jobs"
        job_ids_str = self.redis.smembers(jobs_key)
        return {UUID(job_id) for job_id in job_ids_str}

    def deregister_worker(self, worker_id: str) -> None:
        """
        Deregister a worker (clean shutdown).

        Removes Redis keys and marks worker as STOPPED.

        Args:
            worker_id: Worker identifier
        """
        # Remove Redis keys
        heartbeat_key = f"worker:{worker_id}:heartbeat"
        jobs_key = f"worker:{worker_id}:jobs"
        self.redis.delete(heartbeat_key, jobs_key)

        # Mark as stopped in DB
        worker = self.worker_repo.get_by_id(worker_id)
        if worker:
            worker.status = WorkerStatus.STOPPED
            worker.stopped_at = datetime.now(timezone.utc)
            self.db.commit()

    def cleanup_old_workers(self, older_than_hours: int = 1) -> int:
        """
        Clean up old stopped workers from DB.

        Args:
            older_than_hours: Remove workers stopped longer than this

        Returns:
            int: Number of workers deleted
        """
        cleanup_after_seconds = older_than_hours * 3600  # Convert hours to seconds
        return self.worker_repo.delete_old_stopped_workers(cleanup_after_seconds)
