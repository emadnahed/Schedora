"""Tenant repository for database operations."""

from typing import Any, Dict, List, Optional
from uuid import UUID

from sqlalchemy.orm import Session

from schedora.core.exceptions import TenantNotFoundError
from schedora.models.tenant import Tenant


class TenantRepository:
    """Repository for Tenant database operations."""

    def __init__(self, db: Session):
        """
        Initialize repository with database session.

        Args:
            db: SQLAlchemy database session
        """
        self.db = db

    def create(self, tenant_data: Dict[str, Any]) -> Tenant:
        """
        Create a new tenant in the database.

        Args:
            tenant_data: Dictionary of tenant attributes

        Returns:
            Tenant: Created tenant instance
        """
        tenant = Tenant(**tenant_data)
        self.db.add(tenant)
        self.db.flush()
        self.db.refresh(tenant)
        return tenant

    def get_by_id(self, tenant_id: UUID) -> Optional[Tenant]:
        """
        Retrieve tenant by ID.

        Args:
            tenant_id: Tenant UUID

        Returns:
            Optional[Tenant]: Tenant instance or None if not found
        """
        return self.db.query(Tenant).filter(Tenant.tenant_id == tenant_id).first()

    def get_by_slug(self, slug: str) -> Optional[Tenant]:
        """
        Retrieve tenant by slug.

        Args:
            slug: Tenant slug (URL-friendly identifier)

        Returns:
            Optional[Tenant]: Tenant instance or None if not found
        """
        return self.db.query(Tenant).filter(Tenant.slug == slug).first()

    def get_by_name(self, name: str) -> Optional[Tenant]:
        """
        Retrieve tenant by name.

        Args:
            name: Tenant name

        Returns:
            Optional[Tenant]: Tenant instance or None if not found
        """
        return self.db.query(Tenant).filter(Tenant.name == name).first()

    def get_all(self, active_only: bool = True) -> List[Tenant]:
        """
        Retrieve all tenants.

        Args:
            active_only: If True, only return active tenants

        Returns:
            List[Tenant]: List of tenants
        """
        query = self.db.query(Tenant)
        if active_only:
            query = query.filter(Tenant.is_active == True)
        return query.all()

    def update(self, tenant_id: UUID, updates: Dict[str, Any]) -> Tenant:
        """
        Update tenant fields.

        Args:
            tenant_id: Tenant UUID
            updates: Dictionary of fields to update

        Returns:
            Tenant: Updated tenant instance

        Raises:
            TenantNotFoundError: If tenant not found
        """
        tenant = self.get_by_id(tenant_id)
        if not tenant:
            raise TenantNotFoundError(f"Tenant {tenant_id} not found")

        for key, value in updates.items():
            setattr(tenant, key, value)

        self.db.flush()
        self.db.refresh(tenant)
        return tenant

    def increment_job_count(self, tenant_id: UUID) -> None:
        """
        Increment current job count for tenant.

        Args:
            tenant_id: Tenant UUID

        Raises:
            TenantNotFoundError: If tenant not found
        """
        tenant = self.get_by_id(tenant_id)
        if not tenant:
            raise TenantNotFoundError(f"Tenant {tenant_id} not found")

        tenant.current_job_count += 1
        tenant.total_jobs_created += 1
        self.db.flush()

    def decrement_job_count(self, tenant_id: UUID) -> None:
        """
        Decrement current job count for tenant.

        Args:
            tenant_id: Tenant UUID

        Raises:
            TenantNotFoundError: If tenant not found
        """
        tenant = self.get_by_id(tenant_id)
        if not tenant:
            raise TenantNotFoundError(f"Tenant {tenant_id} not found")

        if tenant.current_job_count > 0:
            tenant.current_job_count -= 1
        self.db.flush()

    def delete(self, tenant_id: UUID) -> None:
        """
        Delete tenant from database.

        Args:
            tenant_id: Tenant UUID

        Raises:
            TenantNotFoundError: If tenant not found
        """
        tenant = self.get_by_id(tenant_id)
        if not tenant:
            raise TenantNotFoundError(f"Tenant {tenant_id} not found")

        self.db.delete(tenant)
        self.db.flush()
