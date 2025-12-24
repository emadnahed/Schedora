"""Worker model for async job execution."""
from datetime import datetime
from typing import Optional, Dict, Any
from sqlalchemy import (
    String,
    Integer,
    CheckConstraint,
    Index,
    DateTime,
    Float,
    Enum as SQLEnum,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column
from schedora.core.database import Base
from schedora.core.enums import WorkerStatus
from schedora.models.base import TimestampMixin


class Worker(Base, TimestampMixin):
    """
    Worker model representing an async job executor instance.

    Tracks worker lifecycle, heartbeat status, job execution metrics,
    and system resource utilization. Each worker can process multiple
    jobs concurrently up to its configured limit.
    """

    __tablename__ = "workers"

    # Primary identification
    worker_id: Mapped[str] = mapped_column(
        String(255), primary_key=True, nullable=False
    )

    # Worker instance details
    hostname: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    pid: Mapped[int] = mapped_column(Integer, nullable=False)
    version: Mapped[str] = mapped_column(String(50), nullable=False)

    # Lifecycle status
    status: Mapped[WorkerStatus] = mapped_column(
        SQLEnum(WorkerStatus, values_callable=lambda x: [e.value for e in x]),
        nullable=False,
        default=WorkerStatus.STARTING,
        index=True,
    )

    # Heartbeat tracking
    last_heartbeat_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True, index=True
    )

    # Lifecycle timestamps
    started_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    stopped_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # Concurrency control
    max_concurrent_jobs: Mapped[int] = mapped_column(
        Integer, nullable=False, default=10
    )
    current_job_count: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, index=True
    )

    # Job execution metrics
    total_jobs_processed: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0
    )
    total_jobs_succeeded: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0
    )
    total_jobs_failed: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0
    )

    # System resource metrics
    cpu_percent: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    memory_percent: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    # Worker capabilities and metadata
    capabilities: Mapped[Optional[Dict[str, Any]]] = mapped_column(
        JSONB, nullable=True, default=dict
    )
    worker_metadata: Mapped[Optional[Dict[str, Any]]] = mapped_column(
        JSONB, nullable=True, default=dict
    )

    # Constraints
    __table_args__ = (
        CheckConstraint(
            "max_concurrent_jobs > 0",
            name="check_max_concurrent_jobs_positive",
        ),
        CheckConstraint(
            "current_job_count >= 0",
            name="check_current_job_count_non_negative",
        ),
        CheckConstraint(
            "current_job_count <= max_concurrent_jobs",
            name="check_current_job_count_not_exceed_max",
        ),
        CheckConstraint(
            "total_jobs_processed >= 0",
            name="check_total_jobs_processed_non_negative",
        ),
        CheckConstraint(
            "total_jobs_succeeded >= 0",
            name="check_total_jobs_succeeded_non_negative",
        ),
        CheckConstraint(
            "total_jobs_failed >= 0",
            name="check_total_jobs_failed_non_negative",
        ),
        CheckConstraint(
            "stopped_at IS NULL OR started_at IS NULL OR stopped_at >= started_at",
            name="check_stopped_after_started",
        ),
        Index("idx_workers_status_heartbeat", "status", "last_heartbeat_at"),
        Index("idx_workers_hostname_pid", "hostname", "pid"),
    )

    def __repr__(self) -> str:
        """Return string representation of Worker."""
        return f"<Worker(worker_id={self.worker_id}, hostname={self.hostname}, status={self.status})>"
