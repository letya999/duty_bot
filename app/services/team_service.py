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
        org_id = await self.team_repo.get_organization_id_by_workspace(workspace_id)
        
        return await self.team_repo.create({
            'workspace_id': workspace_id,
            'organization_id': org_id,
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
            # Use same session to fetch full user object
            from sqlalchemy.future import select
            stmt = select(User).where(User.id == user_id)
            result = await self.team_repo.db.execute(stmt)
            user = result.scalar_one_or_none()
            if user:
                team = await self.team_repo.add_member(team_id, user)

        return team

    async def add_member(self, team_id: int, user: User) -> Team | None:
        """Add member to team with validation (1 user per team in organization)"""
        team = await self.team_repo.get_by_id(team_id)
        if not team:
            return None

        # Validation: 1 user per team in organization
        if team.organization_id:
            existing_teams = await self.team_repo.get_user_teams_in_organization(user.id, team.organization_id)
            # If user is in existing teams, make sure we aren't just adding them to the same team (idempotency check is inside repo, but here we check for *other* teams)
            for et in existing_teams:
                if et.id != team_id:
                    raise ValueError(f"User is already in team '{et.display_name}' in this organization. A user can only be in one team per organization.")

        return await self.team_repo.add_member(team_id, user)

    async def remove_member(self, team_id: int, user: User) -> Team | None:
        """Remove member from team"""
        return await self.team_repo.remove_member(team_id, user)

    async def delete_team(self, team_id: int) -> bool:
        """Delete team"""
        return await self.team_repo.delete(team_id)

    async def merge_teams(self, target_team_id: int, source_team_id: int) -> Team:
        """Merge source_team into target_team and delete source_team (SuperAdmin only)"""
        from sqlalchemy import update
        from sqlalchemy.future import select
        from app.models import team_members, Schedule, Escalation, RotationConfig, Incident
        
        # 1. Members
        source_members_stmt = select(team_members.c.user_id).where(team_members.c.team_id == source_team_id)
        target_members_stmt = select(team_members.c.user_id).where(team_members.c.team_id == target_team_id)
        
        source_members = (await self.team_repo.db.execute(source_members_stmt)).scalars().all()
        target_members = (await self.team_repo.db.execute(target_members_stmt)).scalars().all()
        
        members_to_add = set(source_members) - set(target_members)
        for user_id in members_to_add:
            stmt = team_members.insert().values(user_id=user_id, team_id=target_team_id)
            await self.team_repo.db.execute(stmt)

        # 2. Schedules (handle duplicates)
        source_schedules_stmt = select(Schedule).where(Schedule.team_id == source_team_id)
        source_schedules = (await self.team_repo.db.execute(source_schedules_stmt)).scalars().all()
        for s in source_schedules:
            exists_stmt = select(Schedule).where(
                Schedule.team_id == target_team_id,
                Schedule.user_id == s.user_id,
                Schedule.date == s.date
            )
            exists = (await self.team_repo.db.execute(exists_stmt)).scalar_one_or_none()
            if exists:
                await self.team_repo.db.delete(s)
            else:
                s.team_id = target_team_id

        # 3. Escalations
        stmt = update(Escalation).where(Escalation.team_id == source_team_id).values(team_id=target_team_id)
        await self.team_repo.db.execute(stmt)

        # 4. RotationConfig
        source_config_stmt = select(RotationConfig).where(RotationConfig.team_id == source_team_id)
        source_config = (await self.team_repo.db.execute(source_config_stmt)).scalar_one_or_none()
        if source_config:
            target_config_stmt = select(RotationConfig).where(RotationConfig.team_id == target_team_id)
            target_config = (await self.team_repo.db.execute(target_config_stmt)).scalar_one_or_none()
            if not target_config:
                source_config.team_id = target_team_id
            else:
                await self.team_repo.db.delete(source_config)


        # 6. Delete source team
        await self.team_repo.delete(source_team_id)
        
        await self.team_repo.db.commit()
        return await self.team_repo.get_by_id(target_team_id)
