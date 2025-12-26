"""Repository for Schedule model."""

from datetime import date
from typing import Optional, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import and_
from sqlalchemy.orm import joinedload
from app.models import Schedule, Team
from app.repositories.base_repository import BaseRepository


class ScheduleRepository(BaseRepository[Schedule]):
    """Repository for Schedule (duty assignment) operations."""

    def __init__(self, db: AsyncSession):
        super().__init__(db, Schedule)

    async def get_by_team_and_date(self, team_id: int, duty_date: date, user_id: int | None = None) -> Optional[Schedule]:
        """Get schedule for team on specific date. Optional user_id for many-to-many lookup."""
        stmt = select(Schedule).options(joinedload(Schedule.user)).where(
            Schedule.team_id == team_id,
            Schedule.date == duty_date
        )
        if user_id is not None:
            stmt = stmt.where(Schedule.user_id == user_id)
            
        result = await self.db.execute(stmt)
        return result.scalars().first()

    async def list_by_team_and_date_range(self, team_id: int, start_date: date, end_date: date) -> List[Schedule]:
        """Get schedules for team in date range."""
        stmt = select(Schedule).options(joinedload(Schedule.user)).where(
            Schedule.team_id == team_id,
            Schedule.date >= start_date,
            Schedule.date <= end_date
        ).order_by(Schedule.date)
        result = await self.db.execute(stmt)
        return result.scalars().all()

    async def list_by_user_and_date_range(self, user_id: int, start_date: date, end_date: date, workspace_id: int = None) -> List[Schedule]:
        """Get schedules assigned to user in date range. If workspace_id provided, filters to that workspace only."""
        stmt = select(Schedule).join(Team).options(joinedload(Schedule.user)).where(
            Schedule.user_id == user_id,
            Schedule.date >= start_date,
            Schedule.date <= end_date
        )

        if workspace_id is not None:
            stmt = stmt.where(Team.workspace_id == workspace_id)

        stmt = stmt.order_by(Schedule.date)
        result = await self.db.execute(stmt)
        return result.scalars().all()

    async def list_by_date(self, duty_date: date, workspace_id: int = None) -> List[Schedule]:
        """Get all schedules for a specific date. If workspace_id provided, filters to that workspace only."""
        stmt = select(Schedule).join(Team).options(joinedload(Schedule.user)).where(Schedule.date == duty_date)

        if workspace_id is not None:
            stmt = stmt.where(Team.workspace_id == workspace_id)

        stmt = stmt.order_by(Schedule.team_id)
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

    async def create_or_update_schedule(self, team_id: int, duty_date: date, user_id: int, is_shift: bool = False, commit: bool = True) -> Schedule:
        """Create new schedule or update existing one.
        If is_shift is False, we find any record for (team, date) and update it to maintain 1 user per day.
        If is_shift is True, we allow multiple records for the same (team, date) but different users.
        """
        if not is_shift:
            # For non-shifts, find ANY record for this day and team
            schedule = await self.get_by_team_and_date(team_id, duty_date)
            if schedule:
                schedule.user_id = user_id
                schedule.is_shift = False
            else:
                schedule = Schedule(team_id=team_id, user_id=user_id, date=duty_date, is_shift=False)
                self.db.add(schedule)
        else:
            # For shifts, we check for THIS specific user
            schedule = await self.get_by_team_and_date(team_id, duty_date, user_id=user_id)
            if not schedule:
                schedule = Schedule(team_id=team_id, user_id=user_id, date=duty_date, is_shift=True)
                self.db.add(schedule)
            else:
                schedule.is_shift = True

        if commit:
            await self.db.commit()
            await self.db.refresh(schedule)
        else:
            await self.db.flush()

        return schedule
