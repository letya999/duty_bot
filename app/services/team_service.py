from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from app.models import Team, User


class TeamService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_team(
        self,
        workspace_id: int,
        name: str,
        display_name: str,
        has_shifts: bool = False,
        team_lead_id: int | None = None
    ) -> Team:
        """Create a new team in workspace"""
        team = Team(
            workspace_id=workspace_id,
            name=name,
            display_name=display_name,
            has_shifts=has_shifts,
            team_lead_id=team_lead_id,
        )
        self.db.add(team)
        await self.db.commit()
        await self.db.refresh(team)
        return team

    async def get_team(self, team_id: int, workspace_id: int = None) -> Team | None:
        """Get team by ID, optionally filtered by workspace"""
        stmt = select(Team).options(
            selectinload(Team.members),
            selectinload(Team.team_lead_user)
        ).where(Team.id == team_id)
        if workspace_id is not None:
            stmt = stmt.where(Team.workspace_id == workspace_id)
        result = await self.db.execute(stmt)
        return result.scalars().first()

    async def get_team_by_name(self, workspace_id: int, name: str) -> Team | None:
        """Get team by name in workspace"""
        stmt = select(Team).options(
            selectinload(Team.members),
            selectinload(Team.team_lead_user)
        ).where(
            (Team.workspace_id == workspace_id) &
            (Team.name == name)
        )
        result = await self.db.execute(stmt)
        return result.scalars().first()

    async def get_all_teams(self, workspace_id: int) -> list[Team]:
        """Get all teams in workspace"""
        stmt = select(Team).options(
            selectinload(Team.members),
            selectinload(Team.team_lead_user)
        ).where(Team.workspace_id == workspace_id)
        result = await self.db.execute(stmt)
        return result.scalars().all()

    async def update_team(
        self,
        team: Team,
        name: str | None = None,
        display_name: str | None = None,
        has_shifts: bool | None = None
    ) -> Team:
        """Update team"""
        if name is not None:
            team.name = name
        if display_name is not None:
            team.display_name = display_name
        if has_shifts is not None:
            team.has_shifts = has_shifts

        await self.db.commit()
        await self.db.refresh(team)
        return team

    async def set_team_lead(self, team: Team, user: User) -> Team:
        """Set team lead for team"""
        team.team_lead_id = user.id

        # Add to team members if not already there
        if user not in team.members:
            team.members.append(user)

        await self.db.commit()
        await self.db.refresh(team)
        return team

    async def add_member(self, team: Team, user: User) -> Team:
        """Add member to team"""
        if user not in team.members:
            team.members.append(user)
            await self.db.commit()
            await self.db.refresh(team)

        return team

    async def remove_member(self, team: Team, user: User) -> Team:
        """Remove member from team"""
        if user in team.members:
            team.members.remove(user)
            await self.db.commit()
            await self.db.refresh(team)

        return team

    async def delete_team(self, team: Team):
        """Delete team"""
        await self.db.delete(team)
        await self.db.commit()
