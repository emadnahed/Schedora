"""Workflow model for DAG definitions."""
from uuid import uuid4
from typing import Optional, Dict, Any, List
from sqlalchemy import String, Text, Table, Column, ForeignKey
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship
from schedora.core.database import Base
from schedora.models.base import TimestampMixin

# Association table for workflow-job many-to-many relationship
workflow_jobs = Table(
    "workflow_jobs",
    Base.metadata,
    Column("workflow_id", UUID(as_uuid=True), ForeignKey("workflows.workflow_id"), primary_key=True),
    Column("job_id", UUID(as_uuid=True), ForeignKey("jobs.job_id"), primary_key=True),
)


class Workflow(Base, TimestampMixin):
    """
    Workflow model representing a DAG of jobs.

    A workflow defines a collection of jobs and their execution dependencies.
    Jobs within a workflow can have parent-child relationships forming a DAG.
    """

    __tablename__ = "workflows"

    # Primary identification
    workflow_id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid4
    )

    # Workflow metadata
    name: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Configuration (timeout, notifications, etc.)
    config: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSONB, nullable=True)

    # Relationships
    jobs: Mapped[List["Job"]] = relationship(  # type: ignore
        "Job",
        secondary=workflow_jobs,
        lazy="selectin",
    )

    def __repr__(self) -> str:
        """Return string representation of Workflow."""
        return f"<Workflow(workflow_id={self.workflow_id}, name={self.name})>"
