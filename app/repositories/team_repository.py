"""Repository for Team model."""

from typing import Optional, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload
from app.models import Team
from app.repositories.base_repository import BaseRepository


class TeamRepository(BaseRepository[Team]):
    """Repository for Team operations."""

    def __init__(self, db: AsyncSession):
        super().__init__(db, Team)

    async def get_by_id_with_members(self, team_id: int) -> Optional[Team]:
        """Get team with loaded members relationship."""
        stmt = select(Team).where(Team.id == team_id).options(selectinload(Team.members))
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_name_in_workspace(self, workspace_id: int, team_name: str) -> Optional[Team]:
        """Get team by name in workspace."""
        stmt = select(Team).where(
            Team.workspace_id == workspace_id,
            Team.name == team_name
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def list_by_workspace(self, workspace_id: int, skip: int = 0, limit: int = 100) -> List[Team]:
        """List all teams in workspace with members loaded."""
        stmt = (
            select(Team)
            .where(Team.workspace_id == workspace_id)
            .options(selectinload(Team.members))
            .offset(skip)
            .limit(limit)
        )
        result = await self.db.execute(stmt)
        return result.scalars().all()

    async def update_team_info(self, team_id: int, name: str, display_name: str, has_shifts: bool) -> Optional[Team]:
        """Update team basic information."""
        team = await self.get_by_id(team_id)
        if team:
            team.name = name
            team.display_name = display_name
            team.has_shifts = has_shifts
            await self.db.commit()
            await self.db.refresh(team)
        return team

    async def set_team_lead(self, team_id: int, user_id: Optional[int]) -> Optional[Team]:
        """Set team lead for a team."""
        team = await self.get_by_id(team_id)
        if team:
            team.team_lead_id = user_id
            await self.db.commit()
            await self.db.refresh(team)
        return team
