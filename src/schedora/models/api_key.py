"""API Key model for programmatic authentication."""

from datetime import datetime
from typing import TYPE_CHECKING, Optional
from uuid import UUID, uuid4

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from schedora.core.database import Base
from schedora.models.base import TimestampMixin

if TYPE_CHECKING:
    from schedora.models.user import User


class ApiKey(Base, TimestampMixin):
    """
    API Key model for service-to-service authentication.

    API keys provide long-lived credentials for programmatic access.
    Keys are hashed (like passwords) for secure storage.
    """

    __tablename__ = "api_keys"

    # Primary Key
    key_id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)

    # Owner
    user_id: Mapped[UUID] = mapped_column(
        ForeignKey("users.user_id", ondelete="CASCADE"), nullable=False, index=True
    )

    # Key Data
    key_hash: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    key_prefix: Mapped[str] = mapped_column(
        String(20), nullable=False
    )  # For display (e.g., "sk_live_abc")

    # Metadata
    name: Mapped[str] = mapped_column(String(100), nullable=False)  # User-friendly name

    # Status
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, index=True)
    expires_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    revoked_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    # Usage Tracking
    last_used_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    usage_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="api_keys")

    def __repr__(self) -> str:
        return f"<ApiKey(key_id={self.key_id}, name='{self.name}', prefix='{self.key_prefix}')>"

    def is_valid(self) -> bool:
        """Check if API key is valid (active and not expired)."""
        if not self.is_active or self.revoked_at is not None:
            return False

        if self.expires_at is not None:
            return datetime.utcnow() < self.expires_at

        return True

    def is_expired(self) -> bool:
        """Check if API key has expired."""
        if self.expires_at is None:
            return False
        return datetime.utcnow() >= self.expires_at
