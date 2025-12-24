"""Job model for distributed job orchestration."""
from datetime import datetime, timezone
from uuid import uuid4
from typing import Optional, Dict, Any, List
from sqlalchemy import (
    String,
    Integer,
    CheckConstraint,
    Index,
    Text,
    DateTime,
    Enum as SQLEnum,
    Table,
    Column,
    ForeignKey,
)
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship
from schedora.core.database import Base
from schedora.core.enums import JobStatus, RetryPolicy
from schedora.models.base import TimestampMixin

# Job dependencies table for DAG support (many-to-many self-referential)
job_dependencies = Table(
    "job_dependencies",
    Base.metadata,
    Column("job_id", UUID(as_uuid=True), ForeignKey("jobs.job_id"), primary_key=True),
    Column("depends_on_job_id", UUID(as_uuid=True), ForeignKey("jobs.job_id"), primary_key=True),
)


class Job(Base, TimestampMixin):
    """
    Job model representing a unit of work in the orchestration system.

    Implements a persistent state machine for job execution tracking.
    Supports DAG workflows, retries with backoff, and idempotent execution.
    """

    __tablename__ = "jobs"

    # Primary identification
    job_id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid4
    )

    # Job classification
    type: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    payload: Mapped[Dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)

    # Scheduling & Priority
    priority: Mapped[int] = mapped_column(Integer, nullable=False, default=5, index=True)
    scheduled_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        index=True,
    )

    # Retry & Timeout configuration
    max_retries: Mapped[int] = mapped_column(Integer, nullable=False, default=3)
    retry_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    retry_policy: Mapped[RetryPolicy] = mapped_column(
        SQLEnum(RetryPolicy, values_callable=lambda x: [e.value for e in x]),
        nullable=False,
        default=RetryPolicy.EXPONENTIAL,
    )
    timeout_seconds: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    # Idempotency
    idempotency_key: Mapped[str] = mapped_column(
        String(255), unique=True, nullable=False, index=True
    )

    # State Machine
    status: Mapped[JobStatus] = mapped_column(
        SQLEnum(JobStatus, values_callable=lambda x: [e.value for e in x]),
        nullable=False,
        default=JobStatus.PENDING,
        index=True,
    )

    # DAG Support (Phase 2)
    parent_job_id: Mapped[Optional[UUID]] = mapped_column(
        UUID(as_uuid=True), nullable=True, index=True
    )

    # Execution tracking
    started_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    completed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    worker_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)

    # Error tracking
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    error_details: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSONB, nullable=True)

    # Result storage
    result: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSONB, nullable=True)

    # Constraints
    __table_args__ = (
        CheckConstraint("priority >= 0 AND priority <= 10", name="check_priority_range"),
        CheckConstraint("max_retries >= 0", name="check_max_retries_non_negative"),
        CheckConstraint("retry_count >= 0", name="check_retry_count_non_negative"),
        CheckConstraint(
            "retry_count <= max_retries", name="check_retry_count_not_exceed_max"
        ),
        CheckConstraint("timeout_seconds IS NULL OR timeout_seconds > 0", name="check_timeout_positive"),
        CheckConstraint(
            "completed_at IS NULL OR started_at IS NULL OR completed_at >= started_at",
            name="check_completed_after_started",
        ),
        Index("idx_jobs_status_scheduled_at", "status", "scheduled_at"),
        Index("idx_jobs_created_at_desc", "created_at", postgresql_using="btree"),
    )

    # Relationships

    # Workflow membership: workflows this job belongs to
    workflows: Mapped[List["Workflow"]] = relationship(  # type: ignore
        "Workflow",
        secondary="workflow_jobs",
        back_populates="jobs",
        lazy="selectin",
    )

    # DAG dependencies: jobs that this job depends on
    dependencies: Mapped[List["Job"]] = relationship(
        "Job",
        secondary=job_dependencies,
        primaryjoin="Job.job_id==job_dependencies.c.job_id",
        secondaryjoin="Job.job_id==job_dependencies.c.depends_on_job_id",
        back_populates="dependents",
        lazy="selectin",
    )

    # DAG dependents: jobs that depend on this job
    dependents: Mapped[List["Job"]] = relationship(
        "Job",
        secondary=job_dependencies,
        primaryjoin="Job.job_id==job_dependencies.c.depends_on_job_id",
        secondaryjoin="Job.job_id==job_dependencies.c.job_id",
        back_populates="dependencies",
        lazy="selectin",
        overlaps="dependencies",
    )

    def __repr__(self) -> str:
        """Return string representation of Job."""
        return f"<Job(job_id={self.job_id}, type={self.type}, status={self.status})>"
