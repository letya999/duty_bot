"""Repository for DutyStats model."""

from datetime import date, datetime
from typing import Optional, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import and_, func
from sqlalchemy.orm import selectinload
from app.models import DutyStats, Team, User, Schedule, Shift
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

    async def get_user_monthly_stats(self, workspace_id: int, user_id: int, year: int, month: int) -> List[DutyStats]:
        """Get monthly statistics for a specific user across all teams."""
        stmt = select(DutyStats).where(
            and_(
                DutyStats.workspace_id == workspace_id,
                DutyStats.user_id == user_id,
                DutyStats.year == year,
                DutyStats.month == month,
            )
        ).options(selectinload(DutyStats.team))
        result = await self.db.execute(stmt)
        return result.scalars().all()

    async def get_team_monthly_stats(self, workspace_id: int, team_id: int, year: int, month: int) -> List[DutyStats]:
        """Get monthly statistics for a specific team across all users."""
        stmt = select(DutyStats).where(
            and_(
                DutyStats.workspace_id == workspace_id,
                DutyStats.team_id == team_id,
                DutyStats.year == year,
                DutyStats.month == month,
            )
        ).options(selectinload(DutyStats.user)).order_by(DutyStats.duty_days.desc())
        result = await self.db.execute(stmt)
        return result.scalars().all()

    async def get_workspace_monthly_stats(self, workspace_id: int, year: int, month: int) -> List[DutyStats]:
        """Get all statistics for workspace in a given month."""
        stmt = select(DutyStats).where(
            and_(
                DutyStats.workspace_id == workspace_id,
                DutyStats.year == year,
                DutyStats.month == month,
            )
        ).options(selectinload(DutyStats.user), selectinload(DutyStats.team)).order_by(DutyStats.duty_days.desc())
        result = await self.db.execute(stmt)
        return result.scalars().all()

    async def get_user_annual_stats(self, workspace_id: int, user_id: int, year: int) -> List[DutyStats]:
        """Get annual statistics for a user."""
        stmt = select(DutyStats).where(
            and_(
                DutyStats.workspace_id == workspace_id,
                DutyStats.user_id == user_id,
                DutyStats.year == year,
            )
        ).options(selectinload(DutyStats.team)).order_by(DutyStats.month)
        result = await self.db.execute(stmt)
        return result.scalars().all()

    async def get_team_annual_stats(self, workspace_id: int, team_id: int, year: int) -> List[DutyStats]:
        """Get annual statistics for a team."""
        stmt = select(DutyStats).where(
            and_(
                DutyStats.workspace_id == workspace_id,
                DutyStats.team_id == team_id,
                DutyStats.year == year,
            )
        ).options(selectinload(DutyStats.user)).order_by(DutyStats.month, DutyStats.duty_days.desc())
        result = await self.db.execute(stmt)
        return result.scalars().all()

    async def get_top_users_by_duties(self, workspace_id: int, year: int, month: int, limit: int = 10) -> List[dict]:
        """Get top users by duty count in a month."""
        result = await self.db.execute(
            select(
                User.id,
                User.display_name,
                func.sum(DutyStats.duty_days).label("total_duties"),
            )
            .join(User, DutyStats.user_id == User.id)
            .where(
                and_(
                    DutyStats.workspace_id == workspace_id,
                    DutyStats.year == year,
                    DutyStats.month == month,
                )
            )
            .group_by(User.id, User.display_name)
            .order_by(func.sum(DutyStats.duty_days).desc())
            .limit(limit)
        )
        rows = result.all()
        return [
            {"user_id": row[0], "display_name": row[1], "total_duties": row[2]}
            for row in rows
        ]

    async def get_team_workload(self, workspace_id: int, year: int, month: int) -> List[dict]:
        """Get workload distribution across teams."""
        result = await self.db.execute(
            select(
                Team.id,
                Team.display_name,
                func.sum(DutyStats.duty_days).label("total_duties"),
                func.count(func.distinct(DutyStats.user_id)).label("team_members"),
            )
            .join(Team, DutyStats.team_id == Team.id)
            .where(
                and_(
                    DutyStats.workspace_id == workspace_id,
                    DutyStats.year == year,
                    DutyStats.month == month,
                )
            )
            .group_by(Team.id, Team.display_name)
            .order_by(func.sum(DutyStats.duty_days).desc())
        )
        rows = result.all()
        return [
            {
                "team_id": row[0],
                "team_name": row[1],
                "total_duties": row[2],
                "team_members": row[3],
            }
            for row in rows
        ]

    async def batch_update_stats(self, workspace_id: int, year: int, month: int, stats_list: List[dict]) -> None:
        """Batch update multiple stats records."""
        for stat_data in stats_list:
            stats = await self.get_or_create(
                workspace_id,
                stat_data['team_id'],
                stat_data['user_id'],
                year,
                month
            )
            stats.duty_days = stat_data.get('duty_days', 0)
            stats.shift_days = stat_data.get('shift_days', 0)
            stats.updated_at = datetime.utcnow()

        await self.db.commit()
