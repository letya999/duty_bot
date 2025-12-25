"""Repository for Schedule model."""

from datetime import date
from typing import Optional, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from app.models import Schedule
from app.repositories.base_repository import BaseRepository


class ScheduleRepository(BaseRepository[Schedule]):
    """Repository for Schedule (duty assignment) operations."""

    def __init__(self, db: AsyncSession):
        super().__init__(db, Schedule)

    async def get_by_team_and_date(self, team_id: int, duty_date: date) -> Optional[Schedule]:
        """Get schedule for team on specific date."""
        stmt = select(Schedule).where(
            Schedule.team_id == team_id,
            Schedule.date == duty_date
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def list_by_team_and_date_range(self, team_id: int, start_date: date, end_date: date) -> List[Schedule]:
        """Get schedules for team in date range."""
        stmt = select(Schedule).where(
            Schedule.team_id == team_id,
            Schedule.date >= start_date,
            Schedule.date <= end_date
        ).order_by(Schedule.date)
        result = await self.db.execute(stmt)
        return result.scalars().all()

    async def list_by_user_and_date_range(self, user_id: int, start_date: date, end_date: date) -> List[Schedule]:
        """Get schedules assigned to user in date range."""
        stmt = select(Schedule).where(
            Schedule.user_id == user_id,
            Schedule.date >= start_date,
            Schedule.date <= end_date
        ).order_by(Schedule.date)
        result = await self.db.execute(stmt)
        return result.scalars().all()

    async def list_by_date(self, duty_date: date) -> List[Schedule]:
        """Get all schedules for a specific date."""
        stmt = select(Schedule).where(Schedule.date == duty_date).order_by(Schedule.team_id)
        result = await self.db.execute(stmt)
        return result.scalars().all()

    async def delete_by_team_and_date(self, team_id: int, duty_date: date) -> bool:
        """Delete schedule for team on specific date."""
        schedule = await self.get_by_team_and_date(team_id, duty_date)
        if schedule:
            await self.db.delete(schedule)
            await self.db.commit()
            return True
        return False

    async def create_or_update_schedule(self, team_id: int, duty_date: date, user_id: int) -> Schedule:
        """Create new schedule or update existing one."""
        schedule = await self.get_by_team_and_date(team_id, duty_date)

        if schedule:
            schedule.user_id = user_id
            await self.db.commit()
            await self.db.refresh(schedule)
        else:
            schedule = await self.create({
                'team_id': team_id,
                'date': duty_date,
                'user_id': user_id,
            })

        return schedule
