"""Tenant model for multi-tenancy support."""

from datetime import datetime
from typing import TYPE_CHECKING, Dict, Any, List, Optional
from uuid import UUID, uuid4

from sqlalchemy import Boolean, CheckConstraint, Integer, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from schedora.core.database import Base
from schedora.models.base import TimestampMixin

if TYPE_CHECKING:
    from schedora.models.user import User
    from schedora.models.job import Job
    from schedora.models.workflow import Workflow
    from schedora.models.worker import Worker


class Tenant(Base, TimestampMixin):
    """
    Tenant model for multi-tenancy and resource quotas.

    Tenants represent isolated environments for different organizations
    or projects, each with their own users, jobs, and resource limits.
    """

    __tablename__ = "tenants"

    # Primary Key
    tenant_id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)

    # Identity
    name: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    slug: Mapped[str] = mapped_column(
        String(100), unique=True, nullable=False, index=True
    )

    # Resource Quotas
    max_jobs_per_day: Mapped[int] = mapped_column(Integer, nullable=False, default=10000)
    max_concurrent_jobs: Mapped[int] = mapped_column(Integer, nullable=False, default=100)
    max_workers: Mapped[int] = mapped_column(Integer, nullable=False, default=10)

    # Current Usage Tracking
    current_job_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    total_jobs_created: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    # Status
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, index=True)

    # Configuration (flexible JSONB for tenant-specific settings)
    settings: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSONB, nullable=True)

    # Relationships
    users: Mapped[List["User"]] = relationship("User", back_populates="tenant", lazy="select")
    jobs: Mapped[List["Job"]] = relationship("Job", back_populates="tenant", lazy="select")
    workflows: Mapped[List["Workflow"]] = relationship(
        "Workflow", back_populates="tenant", lazy="select"
    )
    workers: Mapped[List["Worker"]] = relationship("Worker", back_populates="tenant", lazy="select")

    __table_args__ = (
        CheckConstraint("max_jobs_per_day > 0", name="check_max_jobs_per_day_positive"),
        CheckConstraint("max_concurrent_jobs > 0", name="check_max_concurrent_jobs_positive"),
        CheckConstraint("max_workers > 0", name="check_max_workers_positive"),
        CheckConstraint("current_job_count >= 0", name="check_current_job_count_non_negative"),
        CheckConstraint("total_jobs_created >= 0", name="check_total_jobs_created_non_negative"),
    )

    def __repr__(self) -> str:
        return f"<Tenant(tenant_id={self.tenant_id}, name='{self.name}', slug='{self.slug}')>"

    def is_quota_exceeded(self) -> bool:
        """Check if tenant has exceeded concurrent job quota."""
        return self.current_job_count >= self.max_concurrent_jobs

    def can_create_job(self) -> bool:
        """Check if tenant can create a new job (within quota)."""
        return self.is_active and not self.is_quota_exceeded()
