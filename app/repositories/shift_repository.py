"""Repository for Shift model."""

from datetime import date
from typing import Optional, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload
from app.models import Shift
from app.repositories.base_repository import BaseRepository


class ShiftRepository(BaseRepository[Shift]):
    """Repository for Shift operations."""

    def __init__(self, db: AsyncSession):
        super().__init__(db, Shift)

    async def get_by_id_with_users(self, shift_id: int) -> Optional[Shift]:
        """Get shift with loaded users relationship."""
        stmt = select(Shift).where(Shift.id == shift_id).options(selectinload(Shift.users))
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_team_and_date(self, team_id: int, shift_date: date) -> Optional[Shift]:
        """Get shift for team on specific date."""
        stmt = select(Shift).where(
            Shift.team_id == team_id,
            Shift.date == shift_date
        ).options(selectinload(Shift.users))
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def list_by_team_and_date_range(self, team_id: int, start_date: date, end_date: date) -> List[Shift]:
        """Get shifts for team in date range."""
        stmt = select(Shift).where(
            Shift.team_id == team_id,
            Shift.date >= start_date,
            Shift.date <= end_date
        ).options(selectinload(Shift.users)).order_by(Shift.date)
        result = await self.db.execute(stmt)
        return result.scalars().all()

    async def list_by_user_and_date_range(self, user_id: int, start_date: date, end_date: date) -> List[Shift]:
        """Get shifts assigned to user in date range."""
        from sqlalchemy import and_
        stmt = select(Shift).join(Shift.users).where(
            Shift.users.any(id=user_id),
            Shift.date >= start_date,
            Shift.date <= end_date
        ).order_by(Shift.date)
        result = await self.db.execute(stmt)
        return result.scalars().all()

    async def delete_by_team_and_date(self, team_id: int, shift_date: date) -> bool:
        """Delete shift for team on specific date."""
        shift = await self.get_by_team_and_date(team_id, shift_date)
        if shift:
            await self.db.delete(shift)
            await self.db.commit()
            return True
        return False
