"""User model for authentication and authorization."""

from datetime import datetime
from typing import TYPE_CHECKING, List, Optional
from uuid import UUID, uuid4

from sqlalchemy import Boolean, CheckConstraint, DateTime, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from schedora.core.database import Base
from schedora.models.base import TimestampMixin

if TYPE_CHECKING:
    from schedora.models.tenant import Tenant
    from schedora.models.api_key import ApiKey
    from schedora.models.job import Job
    from schedora.models.workflow import Workflow


class User(Base, TimestampMixin):
    """
    User model for authentication and authorization.

    Users belong to tenants and have roles that determine their permissions.
    Supported roles: 'admin' (full access) and 'user' (limited access).
    """

    __tablename__ = "users"

    # Primary Key
    user_id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)

    # Authentication Credentials
    username: Mapped[str] = mapped_column(String(100), unique=True, nullable=False, index=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)

    # Authorization
    role: Mapped[str] = mapped_column(
        String(50), nullable=False, default="user", index=True
    )  # 'admin' or 'user'

    # Status
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    # Multi-Tenancy
    tenant_id: Mapped[Optional[UUID]] = mapped_column(
        ForeignKey("tenants.tenant_id", ondelete="CASCADE"), nullable=True, index=True
    )

    # Activity Tracking
    last_login_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # Relationships
    tenant: Mapped[Optional["Tenant"]] = relationship("Tenant", back_populates="users")
    api_keys: Mapped[List["ApiKey"]] = relationship(
        "ApiKey", back_populates="user", cascade="all, delete-orphan", lazy="select"
    )
    jobs: Mapped[List["Job"]] = relationship("Job", back_populates="user", lazy="select")
    workflows: Mapped[List["Workflow"]] = relationship("Workflow", back_populates="user", lazy="select")

    __table_args__ = (
        CheckConstraint("role IN ('admin', 'user')", name="check_role"),
    )

    def __repr__(self) -> str:
        return f"<User(user_id={self.user_id}, username='{self.username}', role='{self.role}')>"

    def is_admin(self) -> bool:
        """Check if user has admin role."""
        return self.role == "admin"

    def is_user(self) -> bool:
        """Check if user has user role."""
        return self.role == "user"
