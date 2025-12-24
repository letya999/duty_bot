"""Repository for DutyStats model."""

from datetime import date
from typing import Optional, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import and_
from app.models import DutyStats
from app.repositories.base_repository import BaseRepository


class DutyStatsRepository(BaseRepository[DutyStats]):
    """Repository for DutyStats operations."""

    def __init__(self, db: AsyncSession):
        super().__init__(db, DutyStats)

    async def get_or_create(self, workspace_id: int, team_id: int, user_id: int, year: int, month: int) -> DutyStats:
        """Get or create stats entry for user/team/period."""
        stmt = select(DutyStats).where(
            and_(
                DutyStats.workspace_id == workspace_id,
                DutyStats.team_id == team_id,
                DutyStats.user_id == user_id,
                DutyStats.year == year,
                DutyStats.month == month,
            )
        )
        result = await self.db.execute(stmt)
        stats = result.scalar_one_or_none()

        if not stats:
            stats = DutyStats(
                workspace_id=workspace_id,
                team_id=team_id,
                user_id=user_id,
                year=year,
                month=month,
                duty_days=0,
                shift_days=0,
            )
            self.db.add(stats)
            await self.db.commit()
            await self.db.refresh(stats)

        return stats

    async def list_by_workspace_and_period(self, workspace_id: int, year: int, month: int) -> List[DutyStats]:
        """List all stats for workspace in given period."""
        stmt = select(DutyStats).where(
            and_(
                DutyStats.workspace_id == workspace_id,
                DutyStats.year == year,
                DutyStats.month == month,
            )
        ).order_by(DutyStats.duty_days.desc())
        result = await self.db.execute(stmt)
        return result.scalars().all()

    async def list_by_team_and_period(self, team_id: int, year: int, month: int) -> List[DutyStats]:
        """List all stats for team in given period."""
        stmt = select(DutyStats).where(
            and_(
                DutyStats.team_id == team_id,
                DutyStats.year == year,
                DutyStats.month == month,
            )
        ).order_by(DutyStats.duty_days.desc())
        result = await self.db.execute(stmt)
        return result.scalars().all()

    async def increment_duty_days(self, workspace_id: int, team_id: int, user_id: int, year: int, month: int, count: int = 1) -> DutyStats:
        """Increment duty days count for user."""
        stats = await self.get_or_create(workspace_id, team_id, user_id, year, month)
        stats.duty_days += count
        await self.db.commit()
        await self.db.refresh(stats)
        return stats

    async def increment_shift_days(self, workspace_id: int, team_id: int, user_id: int, year: int, month: int, count: int = 1) -> DutyStats:
        """Increment shift days count for user."""
        stats = await self.get_or_create(workspace_id, team_id, user_id, year, month)
        stats.shift_days += count
        await self.db.commit()
        await self.db.refresh(stats)
        return stats

    async def set_hours_worked(self, workspace_id: int, team_id: int, user_id: int, year: int, month: int, hours: int) -> DutyStats:
        """Set hours worked for user."""
        stats = await self.get_or_create(workspace_id, team_id, user_id, year, month)
        stats.hours_worked = hours
        await self.db.commit()
        await self.db.refresh(stats)
        return stats
