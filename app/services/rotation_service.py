from datetime import date
from app.models import RotationConfig, Team, User, Schedule
from app.repositories import RotationConfigRepository, ScheduleRepository, UserRepository


class RotationService:
    def __init__(self, rotation_config_repo: RotationConfigRepository, schedule_repo: ScheduleRepository = None, user_repo: UserRepository = None):
        self.rotation_config_repo = rotation_config_repo
        self.schedule_repo = schedule_repo
        self.user_repo = user_repo

    async def enable_rotation(
        self,
        team: Team,
        member_ids: list[int]
    ) -> RotationConfig:
        """Enable automatic rotation for a team with specific member order"""
        return await self.rotation_config_repo.enable_rotation(team.id, member_ids)

    async def disable_rotation(self, team: Team) -> bool:
        """Disable automatic rotation for a team"""
        config = await self.rotation_config_repo.toggle_enabled(team.id, False)
        return config is not None

    async def get_rotation_config(self, team: Team) -> RotationConfig | None:
        """Get rotation configuration for a team"""
        return await self.rotation_config_repo.get_by_team(team.id)

    async def get_next_person(
        self,
        team: Team,
        rotation_date: date
    ) -> User | None:
        """Get the next person in rotation queue"""
        config = await self.get_rotation_config(team)

        if not config or not config.enabled or not config.member_ids:
            return None

        # Get member IDs in order
        member_ids = config.member_ids
        if not member_ids:
            return None

        # Find current index
        if config.last_assigned_user_id in member_ids:
            current_index = member_ids.index(config.last_assigned_user_id)
            next_index = (current_index + 1) % len(member_ids)
        else:
            # If last assigned user is not in list, start from beginning
            next_index = 0

        next_user_id = member_ids[next_index]

        # Fetch user from database
        if self.user_repo:
            return await self.user_repo.get_by_id(next_user_id)

        # Fallback: create a stub user object with just the ID
        return User(id=next_user_id)

    async def assign_rotation(
        self,
        team: Team,
        assignment_date: date
    ) -> tuple[User | None, str]:
        """Automatically assign next person in rotation to a date

        Returns: tuple of (assigned_user, message)
        """
        config = await self.get_rotation_config(team)

        if not config or not config.enabled:
            return None, "Rotation is not enabled for this team"

        # Get next person
        next_person = await self.get_next_person(team, assignment_date)

        if not next_person:
            return None, "No members configured for rotation"

        # Update or create schedule
        if self.schedule_repo:
            await self.schedule_repo.create_or_update_schedule(team.id, assignment_date, next_person.id)

        # Update rotation config
        config = await self.rotation_config_repo.update_last_assigned_for_rotation(
            team.id, next_person.id, assignment_date
        )

        return next_person, f"Assigned {next_person.display_name} to {assignment_date.strftime('%d.%m.%Y')}"

    async def update_member_order(
        self,
        team: Team,
        member_ids: list[int]
    ) -> RotationConfig:
        """Update the member order in rotation"""
        config = await self.get_rotation_config(team)

        if not config:
            raise ValueError(f"No rotation config for team {team.id}")

        return await self.rotation_config_repo.update_member_list(team.id, member_ids)

    async def get_rotation_status(self, team: Team) -> str:
        """Get human-readable rotation status"""
        config = await self.get_rotation_config(team)

        if not config:
            return "No rotation configured"

        if not config.enabled:
            return "Rotation is disabled"

        members_text = "No members"
        if config.member_ids and self.user_repo:
            # Fetch member names
            users = []
            for uid in config.member_ids:
                user = await self.user_repo.get_by_id(uid)
                if user:
                    users.append(user)

            user_map = {u.id: u.display_name for u in users}
            members_list = [user_map.get(uid, f"User {uid}") for uid in config.member_ids]
            members_text = " → ".join(members_list)

        last_assigned = ""
        if config.last_assigned_user_id and config.last_assigned_date:
            if self.user_repo:
                user = await self.user_repo.get_by_id(config.last_assigned_user_id)
                if user:
                    last_assigned = f"\nLast assigned: {user.display_name} on {config.last_assigned_date.strftime('%d.%m.%Y')}"
            else:
                last_assigned = f"\nLast assigned: User {config.last_assigned_user_id} on {config.last_assigned_date.strftime('%d.%m.%Y')}"

        return f"**Rotation enabled**\nOrder: {members_text}{last_assigned}"
