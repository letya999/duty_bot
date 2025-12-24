"""Repository for Escalation model."""

from typing import Optional, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from app.models import Escalation
from app.repositories.base_repository import BaseRepository


class EscalationRepository(BaseRepository[Escalation]):
    """Repository for Escalation operations."""

    def __init__(self, db: AsyncSession):
        super().__init__(db, Escalation)

    async def get_by_team(self, team_id: int) -> Optional[Escalation]:
        """Get escalation config for team."""
        stmt = select(Escalation).where(Escalation.team_id == team_id)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_global_cto(self) -> Optional[Escalation]:
        """Get global CTO escalation (team_id is NULL)."""
        stmt = select(Escalation).where(Escalation.team_id == None)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def list_by_team_id(self, team_id: int) -> List[Escalation]:
        """List all escalations for team."""
        stmt = select(Escalation).where(Escalation.team_id == team_id)
        result = await self.db.execute(stmt)
        return result.scalars().all()

    async def set_cto(self, escalation_id: int, user_id: Optional[int]) -> Optional[Escalation]:
        """Set CTO for escalation."""
        escalation = await self.get_by_id(escalation_id)
        if escalation:
            escalation.cto_id = user_id
            await self.db.commit()
            await self.db.refresh(escalation)
        return escalation
