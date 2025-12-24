from datetime import date
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from app.models import RotationConfig, Team, User, Schedule


class RotationService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def enable_rotation(
        self,
        team: Team,
        member_ids: list[int]
    ) -> RotationConfig:
        """Enable automatic rotation for a team with specific member order"""
        # Check if rotation config already exists
        stmt = select(RotationConfig).where(RotationConfig.team_id == team.id)
        result = await self.db.execute(stmt)
        rotation_config = result.scalars().first()

        if rotation_config:
            # Update existing config
            rotation_config.enabled = True
            rotation_config.member_ids = member_ids
            if not rotation_config.last_assigned_user_id:
                # Set first member as initial last assigned
                rotation_config.last_assigned_user_id = member_ids[0]
        else:
            # Create new config
            rotation_config = RotationConfig(
                team_id=team.id,
                enabled=True,
                member_ids=member_ids,
                last_assigned_user_id=member_ids[0] if member_ids else None,
            )
            self.db.add(rotation_config)

        await self.db.commit()
        await self.db.refresh(rotation_config)
        return rotation_config

    async def disable_rotation(self, team: Team) -> bool:
        """Disable automatic rotation for a team"""
        stmt = select(RotationConfig).where(RotationConfig.team_id == team.id)
        result = await self.db.execute(stmt)
        rotation_config = result.scalars().first()

        if rotation_config:
            rotation_config.enabled = False
            await self.db.commit()
            return True

        return False

    async def get_rotation_config(self, team: Team) -> RotationConfig | None:
        """Get rotation configuration for a team"""
        stmt = select(RotationConfig).options(
            selectinload(RotationConfig.last_assigned_user)
        ).where(RotationConfig.team_id == team.id)
        result = await self.db.execute(stmt)
        return result.scalars().first()

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
        stmt = select(User).where(User.id == next_user_id)
        result = await self.db.execute(stmt)
        return result.scalars().first()

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

        # Check if there's already a schedule for this date
        stmt = select(Schedule).where(
            (Schedule.team_id == team.id) & (Schedule.date == assignment_date)
        )
        result = await self.db.execute(stmt)
        existing_schedule = result.scalars().first()

        # Update or create schedule
        if existing_schedule:
            existing_schedule.user_id = next_person.id
        else:
            schedule = Schedule(
                team_id=team.id,
                user_id=next_person.id,
                date=assignment_date,
            )
            self.db.add(schedule)

        # Update rotation config
        config.last_assigned_user_id = next_person.id
        config.last_assigned_date = assignment_date

        await self.db.commit()

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

        config.member_ids = member_ids
        await self.db.commit()
        await self.db.refresh(config)
        return config

    async def get_rotation_status(self, team: Team) -> str:
        """Get human-readable rotation status"""
        config = await self.get_rotation_config(team)

        if not config:
            return "No rotation configured"

        if not config.enabled:
            return "Rotation is disabled"

        members_text = "No members"
        if config.member_ids:
            # Fetch member names
            stmt = select(User).where(User.id.in_(config.member_ids))
            result = await self.db.execute(stmt)
            users = result.scalars().all()
            user_map = {u.id: u.display_name for u in users}
            members_list = [user_map.get(uid, f"User {uid}") for uid in config.member_ids]
            members_text = " → ".join(members_list)

        last_assigned = ""
        if config.last_assigned_user_id and config.last_assigned_date:
            user = config.last_assigned_user
            if user:
                last_assigned = f"\nLast assigned: {user.display_name} on {config.last_assigned_date.strftime('%d.%m.%Y')}"

        return f"**Rotation enabled**\nOrder: {members_text}{last_assigned}"
