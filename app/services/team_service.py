from app.models import Team, User
from app.repositories import TeamRepository


class TeamService:
    def __init__(self, team_repo: TeamRepository):
        self.team_repo = team_repo

    async def create_team(
        self,
        workspace_id: int,
        name: str,
        display_name: str,
        has_shifts: bool = False,
        team_lead_id: int | None = None
    ) -> Team:
        """Create a new team in workspace"""
        return await self.team_repo.create({
            'workspace_id': workspace_id,
            'name': name,
            'display_name': display_name,
            'has_shifts': has_shifts,
            'team_lead_id': team_lead_id,
        })

    async def get_team(self, team_id: int, workspace_id: int = None) -> Team | None:
        """Get team by ID, optionally filtered by workspace"""
        team = await self.team_repo.get_by_id_with_members(team_id)
        if team and workspace_id is not None and team.workspace_id != workspace_id:
            return None
        return team

    async def get_team_by_name(self, workspace_id: int, name: str) -> Team | None:
        """Get team by name in workspace"""
        return await self.team_repo.get_by_name_in_workspace(workspace_id, name)

    async def get_all_teams(self, workspace_id: int) -> list[Team]:
        """Get all teams in workspace"""
        return await self.team_repo.list_by_workspace(workspace_id)

    async def update_team(
        self,
        team_id: int,
        name: str | None = None,
        display_name: str | None = None,
        has_shifts: bool | None = None
    ) -> Team | None:
        """Update team"""
        team = await self.team_repo.get_by_id(team_id)
        if not team:
            return None

        update_data = {}
        if name is not None:
            update_data['name'] = name
        if display_name is not None:
            update_data['display_name'] = display_name
        if has_shifts is not None:
            update_data['has_shifts'] = has_shifts

        if update_data:
            team = await self.team_repo.update(team_id, update_data)
        return team

    async def set_team_lead(self, team_id: int, user_id: int) -> Team | None:
        """Set team lead for team"""
        team = await self.team_repo.get_by_id_with_members(team_id)
        if not team:
            return None

        # Update team_lead_id
        team = await self.team_repo.set_team_lead(team_id, user_id)

        # Add to team members if not already there
        if team and user_id not in [member.id for member in team.members]:
            user = User(id=user_id)
            team.members.append(user)
            await self.team_repo.db.commit()
            await self.team_repo.db.refresh(team)

        return team

    async def add_member(self, team_id: int, user: User) -> Team | None:
        """Add member to team"""
        team = await self.team_repo.get_by_id_with_members(team_id)
        if not team:
            return None

        if user not in team.members:
            team.members.append(user)
            await self.team_repo.db.commit()
            await self.team_repo.db.refresh(team)

        return team

    async def remove_member(self, team_id: int, user: User) -> Team | None:
        """Remove member from team"""
        team = await self.team_repo.get_by_id_with_members(team_id)
        if not team:
            return None

        if user in team.members:
            team.members.remove(user)
            await self.team_repo.db.commit()
            await self.team_repo.db.refresh(team)

        return team

    async def delete_team(self, team_id: int) -> bool:
        """Delete team"""
        return await self.team_repo.delete(team_id)
