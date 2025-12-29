"""Repository for Organization model."""

from typing import Optional, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload
from app.models import Organization
from app.repositories.base_repository import BaseRepository


class OrganizationRepository(BaseRepository[Organization]):
    """Repository for Organization operations."""

    def __init__(self, db: AsyncSession):
        super().__init__(db, Organization)

    async def get_by_name(self, name: str) -> Optional[Organization]:
        """Get organization by name."""
        stmt = select(Organization).where(Organization.name == name)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_with_workspaces(self, organization_id: int) -> Optional[Organization]:
        """Get organization with loaded workspaces."""
        stmt = select(Organization).where(
            Organization.id == organization_id
        ).options(selectinload(Organization.workspaces))
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_with_all_relationships(self, organization_id: int) -> Optional[Organization]:
        """Get organization with all relationships loaded."""
        stmt = select(Organization).where(
            Organization.id == organization_id
        ).options(
            selectinload(Organization.workspaces),
            selectinload(Organization.users),
            selectinload(Organization.teams),
            selectinload(Organization.incidents),
            selectinload(Organization.escalations)
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def list_all_with_workspaces(self, skip: int = 0, limit: int = 100) -> List[Organization]:
        """List all organizations with loaded workspaces."""
        stmt = select(Organization).offset(skip).limit(limit).options(
            selectinload(Organization.workspaces)
        )
        result = await self.db.execute(stmt)
        return result.scalars().all()

    async def get_with_users(self, organization_id: int) -> Optional[Organization]:
        """Get organization with loaded users."""
        stmt = select(Organization).where(
            Organization.id == organization_id
        ).options(selectinload(Organization.users))
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_with_teams(self, organization_id: int) -> Optional[Organization]:
        """Get organization with loaded teams."""
        stmt = select(Organization).where(
            Organization.id == organization_id
        ).options(selectinload(Organization.teams))
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()
