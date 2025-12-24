from datetime import date
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from app.models import Schedule, Team, User


class ScheduleService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def set_duty(
        self,
        team: Team,
        user: User | None,
        duty_date: date
    ) -> Schedule:
        """Set or update duty for a date"""
        stmt = select(Schedule).where(
            (Schedule.team_id == team.id) & (Schedule.date == duty_date)
        )
        result = await self.db.execute(stmt)
        schedule = result.scalars().first()

        if schedule:
            schedule.user_id = user.id if user else None
        else:
            schedule = Schedule(
                team_id=team.id,
                user_id=user.id if user else None,
                date=duty_date,
            )
            self.db.add(schedule)

        await self.db.commit()
        await self.db.refresh(schedule)
        return schedule

    async def get_duty(self, team: Team, duty_date: date) -> Schedule | None:
        """Get duty for a specific date"""
        stmt = select(Schedule).options(
            selectinload(Schedule.user)
        ).where(
            (Schedule.team_id == team.id) & (Schedule.date == duty_date)
        )
        result = await self.db.execute(stmt)
        return result.scalars().first()

    async def get_duties_by_date_range(
        self,
        team: Team,
        start_date: date,
        end_date: date
    ) -> list[Schedule]:
        """Get duties for a date range"""
        stmt = select(Schedule).options(
            selectinload(Schedule.user)
        ).where(
            (Schedule.team_id == team.id) &
            (Schedule.date >= start_date) &
            (Schedule.date <= end_date)
        ).order_by(Schedule.date)
        result = await self.db.execute(stmt)
        return result.scalars().all()

    async def clear_duty(self, team: Team, duty_date: date) -> bool:
        """Clear duty for a date"""
        stmt = select(Schedule).where(
            (Schedule.team_id == team.id) & (Schedule.date == duty_date)
        )
        result = await self.db.execute(stmt)
        schedule = result.scalars().first()

        if schedule:
            await self.db.delete(schedule)
            await self.db.commit()
            return True

        return False

    async def get_today_duty(self, team: Team, today: date) -> User | None:
        """Get today's duty person"""
        schedule = await self.get_duty(team, today)
        return schedule.user if schedule else None

    async def check_user_schedule_conflict(
        self,
        user: User,
        duty_date: date
    ) -> dict | None:
        """Check if user is already scheduled for this date

        Returns: dict with conflict info if conflict exists, None otherwise
        Example: {"user_id": 1, "date": "2024-01-15", "team_name": "Engineering"}
        """
        stmt = select(Schedule).options(
            selectinload(Schedule.team)
        ).where(
            (Schedule.user_id == user.id) & (Schedule.date == duty_date)
        )
        result = await self.db.execute(stmt)
        existing = result.scalars().first()

        if existing and existing.team:
            return {
                "user_id": user.id,
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
        team: Team | None = None
    ) -> Schedule:
        """Update existing duty assignment"""
        stmt = select(Schedule).where(Schedule.id == schedule_id)
        result = await self.db.execute(stmt)
        schedule = result.scalars().first()

        if not schedule:
            raise ValueError(f"Schedule with id {schedule_id} not found")

        schedule.user_id = user_id
        schedule.date = duty_date
        if team:
            schedule.team_id = team.id

        await self.db.commit()
        await self.db.refresh(schedule)
        return schedule
