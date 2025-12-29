"""Repository for Team model."""

from typing import Optional, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload, joinedload
from app.models import Team
from app.repositories.base_repository import BaseRepository


class TeamRepository(BaseRepository[Team]):
    """Repository for Team operations."""

    def __init__(self, db: AsyncSession):
        super().__init__(db, Team)

    async def get_user_teams_in_organization(self, user_id: int, organization_id: int) -> List[Team]:
        """Get all teams a user belongs to in a specific organization."""
        from app.models import team_members
        stmt = select(Team).join(team_members).where(
            team_members.c.user_id == user_id,
            Team.organization_id == organization_id
        )
        result = await self.db.execute(stmt)
        return result.scalars().all()

    async def get_by_id_with_members(self, team_id: int) -> Optional[Team]:
        """Get team with loaded members relationship."""
        stmt = select(Team).where(Team.id == team_id)
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

    async def get_organization_id_by_workspace(self, workspace_id: int) -> Optional[int]:
        """Get organization ID for a workspace."""
        from app.models import Workspace
        stmt = select(Workspace.organization_id).where(Workspace.id == workspace_id)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def list_by_workspace(self, workspace_id: int, skip: int = 0, limit: int = 100) -> List[Team]:
        """List all teams in workspace (or shared organization) with members loaded."""
        from app.models import Workspace
        from sqlalchemy import or_

        # First get the organization_id of the workspace
        organization_id = await self.get_organization_id_by_workspace(workspace_id)
        
        query = select(Team)
        
        if organization_id:
            # If workspace is in an org, show teams from this workspace OR from the organization
            query = query.where(
                or_(
                    Team.workspace_id == workspace_id,
                    Team.organization_id == organization_id
                )
            )
        else:
            # Standard behavior
            query = query.where(Team.workspace_id == workspace_id)
            
        stmt = query.offset(skip).limit(limit)
        
        result = await self.db.execute(stmt)
        # Deduplication is handled by sqlalchemy identity map usually, but distinct might be safer if we had joins.
        # Here we use OR on the same table so result should be unique entities.
        return result.unique().scalars().all()

    async def update_team_info(self, team_id: int, name: str, display_name: str, has_shifts: bool) -> Optional[Team]:
        """Update team basic information."""
        team = await self.get_by_id(team_id)
        if team:
            team.name = name
            team.display_name = display_name
            team.has_shifts = has_shifts
            await self.db.commit()
            return await self.get_by_id_with_members(team_id)
        return None

    async def set_team_lead(self, team_id: int, user_id: Optional[int]) -> Optional[Team]:
        """Set team lead for a team."""
        team = await self.get_by_id(team_id)
        if team:
            team.team_lead_id = user_id
            await self.db.commit()
            # Reload with eager loading to avoid greenlet issues
            team = await self.get_by_id_with_members(team_id)
        return team

    async def add_member(self, team_id: int, user) -> Optional[Team]:
        """Add member to team and return updated team with members loaded."""
        team = await self.get_by_id_with_members(team_id)
        if team:
            # Check by ID to be robust
            if user.id not in [m.id for m in team.members]:
                team.members.append(user)
                await self.db.commit()
                # Reload with eager loading to avoid greenlet issues
                team = await self.get_by_id_with_members(team_id)
        return team

    async def remove_member(self, team_id: int, user) -> Optional[Team]:
        """Remove member from team and return updated team with members loaded."""
        team = await self.get_by_id_with_members(team_id)
        if team:
            # Check by ID to be robust
            member_to_remove = next((m for m in team.members if m.id == user.id), None)
            if member_to_remove:
                team.members.remove(member_to_remove)
                await self.db.commit()
                # Reload with eager loading to avoid greenlet issues
                team = await self.get_by_id_with_members(team_id)
        return team
