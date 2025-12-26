from datetime import date
from sqlalchemy import select
from app.models import Schedule, Team, User
from app.repositories import ScheduleRepository


class ScheduleService:
    def __init__(self, schedule_repo: ScheduleRepository):
        self.schedule_repo = schedule_repo

    async def set_duty(
        self,
        team_id: int,
        user_id: int | None,
        duty_date: date,
        is_shift: bool = False,
        commit: bool = True
    ) -> Schedule:
        """Set or update duty for a date"""
        return await self.schedule_repo.create_or_update_schedule(team_id, duty_date, user_id, is_shift=is_shift, commit=commit)

    async def get_duty(self, team_id: int, duty_date: date) -> Schedule | None:
        """Get duty for a specific date (returns first found)"""
        return await self.schedule_repo.get_by_team_and_date(team_id, duty_date)

    async def get_duties_by_date(self, team_id: int, duty_date: date) -> list[Schedule]:
        """Get all duties/shifts for a specific date and team"""
        stmt = select(Schedule).options(joinedload(Schedule.user)).where(
            Schedule.team_id == team_id,
            Schedule.date == duty_date
        )
        result = await self.schedule_repo.execute(stmt)
        return result.scalars().all()

    async def get_duties_by_date_range(
        self,
        team_id: int,
        start_date: date,
        end_date: date
    ) -> list[Schedule]:
        """Get duties for a date range"""
        return await self.schedule_repo.list_by_team_and_date_range(team_id, start_date, end_date)

    async def clear_duty(self, team_id: int, duty_date: date) -> bool:
        """Clear duty for a date"""
        return await self.schedule_repo.delete_by_team_and_date(team_id, duty_date)

    async def get_today_duty(self, team_id: int, today: date) -> User | None:
        """Get today's primary duty person (returns first found)"""
        schedule = await self.get_duty(team_id, today)
        return schedule.user if schedule else None

    async def get_today_duties(self, team_id: int, today: date) -> list[User]:
        """Get all today's on-duty people for a team"""
        schedules = await self.get_duties_by_date(team_id, today)
        return [s.user for s in schedules if s.user]

    async def check_user_schedule_conflict(
        self,
        user_id: int,
        duty_date: date,
        workspace_id: int = None
    ) -> dict | None:
        """Check if user is already scheduled for this date (optionally filtered by workspace)"""
        stmt = select(Schedule).where(
            Schedule.user_id == user_id,
            Schedule.date == duty_date
        )

        if workspace_id is not None:
            stmt = stmt.join(Team).where(Team.workspace_id == workspace_id)

        result = await self.schedule_repo.execute(stmt)
        existing = result.scalars().first()

        if existing and existing.team:
            return {
                "user_id": user_id,
                "date": str(duty_date),
                "team_name": existing.team.name,
                "team_display_name": existing.team.display_name
            }
        return None

    async def update_duty(
        self,
        schedule_id: int,
        user_id: int,
        duty_date: date,
        team_id: int | None = None
    ) -> Schedule:
        """Update existing duty assignment"""
        schedule = await self.schedule_repo.get_by_id(schedule_id)
        if not schedule:
            raise ValueError(f"Schedule with id {schedule_id} not found")

        update_data = {
            'user_id': user_id,
            'date': duty_date,
        }
        if team_id:
            update_data['team_id'] = team_id

        return await self.schedule_repo.update(schedule_id, update_data)
