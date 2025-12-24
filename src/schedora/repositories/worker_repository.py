"""Worker repository for database operations."""
from typing import Optional, List, Any
from datetime import datetime, timedelta, timezone
from sqlalchemy.orm import Session
from sqlalchemy import and_
from schedora.models.worker import Worker
from schedora.core.enums import WorkerStatus


class WorkerRepository:
    """Repository for Worker database operations."""

    def __init__(self, db: Session):
        """
        Initialize repository with database session.

        Args:
            db: SQLAlchemy database session
        """
        self.db = db

    def create(
        self,
        worker_id: str,
        hostname: str,
        pid: int,
        version: str,
        **kwargs: Any,
    ) -> Worker:
        """
        Create a new worker in the database.

        Args:
            worker_id: Unique worker identifier
            hostname: Worker hostname
            pid: Worker process ID
            version: Worker version
            **kwargs: Additional worker attributes

        Returns:
            Worker: Created worker instance
        """
        worker = Worker(
            worker_id=worker_id,
            hostname=hostname,
            pid=pid,
            version=version,
            **kwargs,
        )
        self.db.add(worker)
        self.db.commit()
        self.db.refresh(worker)
        return worker

    def get_by_id(self, worker_id: str) -> Optional[Worker]:
        """
        Retrieve worker by ID.

        Args:
            worker_id: Worker identifier

        Returns:
            Optional[Worker]: Worker instance or None if not found
        """
        return self.db.query(Worker).filter(Worker.worker_id == worker_id).first()

    def update(self, worker_id: str, **kwargs: Any) -> Worker:
        """
        Update worker fields.

        Args:
            worker_id: Worker identifier
            **kwargs: Fields to update

        Returns:
            Worker: Updated worker instance

        Raises:
            ValueError: If worker not found
        """
        worker = self.get_by_id(worker_id)
        if not worker:
            raise ValueError(f"Worker {worker_id} not found")

        for key, value in kwargs.items():
            setattr(worker, key, value)

        self.db.commit()
        self.db.refresh(worker)
        return worker

    def get_all(self) -> List[Worker]:
        """
        Get all workers regardless of status.

        Returns:
            List[Worker]: List of all workers
        """
        return self.db.query(Worker).all()

    def get_all_active(self) -> List[Worker]:
        """
        Get all workers with ACTIVE status.

        Returns:
            List[Worker]: List of active workers
        """
        return self.db.query(Worker).filter(Worker.status == WorkerStatus.ACTIVE).all()

    def get_all_stale(self, heartbeat_timeout_seconds: int) -> List[Worker]:
        """
        Get all workers that are ACTIVE but have exceeded heartbeat timeout.

        Args:
            heartbeat_timeout_seconds: Seconds before worker considered stale

        Returns:
            List[Worker]: List of stale workers
        """
        timeout_threshold = datetime.now(timezone.utc) - timedelta(
            seconds=heartbeat_timeout_seconds
        )

        return (
            self.db.query(Worker)
            .filter(
                and_(
                    Worker.status == WorkerStatus.ACTIVE,
                    Worker.last_heartbeat_at.isnot(None),
                    Worker.last_heartbeat_at < timeout_threshold,
                )
            )
            .all()
        )

    def increment_current_jobs(self, worker_id: str) -> Worker:
        """
        Increment worker's current job count.

        Args:
            worker_id: Worker identifier

        Returns:
            Worker: Updated worker instance

        Raises:
            ValueError: If worker not found
        """
        worker = self.get_by_id(worker_id)
        if not worker:
            raise ValueError(f"Worker {worker_id} not found")

        worker.current_job_count += 1
        self.db.commit()
        self.db.refresh(worker)
        return worker

    def decrement_current_jobs(self, worker_id: str) -> Worker:
        """
        Decrement worker's current job count (minimum 0).

        Args:
            worker_id: Worker identifier

        Returns:
            Worker: Updated worker instance

        Raises:
            ValueError: If worker not found
        """
        worker = self.get_by_id(worker_id)
        if not worker:
            raise ValueError(f"Worker {worker_id} not found")

        worker.current_job_count = max(0, worker.current_job_count - 1)
        self.db.commit()
        self.db.refresh(worker)
        return worker

    def delete_old_stopped_workers(self, cleanup_after_seconds: int) -> int:
        """
        Delete workers that have been STOPPED for longer than threshold.

        Args:
            cleanup_after_seconds: Seconds after which to delete stopped workers

        Returns:
            int: Number of workers deleted
        """
        cleanup_threshold = datetime.now(timezone.utc) - timedelta(
            seconds=cleanup_after_seconds
        )

        deleted = (
            self.db.query(Worker)
            .filter(
                and_(
                    Worker.status == WorkerStatus.STOPPED,
                    Worker.stopped_at.isnot(None),
                    Worker.stopped_at < cleanup_threshold,
                )
            )
            .delete(synchronize_session=False)
        )

        self.db.commit()
        return deleted
