from datetime import date
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from app.models import Shift, Team, User


class ShiftService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_shift(
        self,
        team: Team,
        shift_date: date,
        users: list[User] | None = None
    ) -> Shift:
        """Create or update shift for a date"""
        stmt = select(Shift).options(
            selectinload(Shift.users)
        ).where(
            (Shift.team_id == team.id) & (Shift.date == shift_date)
        )
        result = await self.db.execute(stmt)
        shift = result.scalars().first()

        if shift:
            # Replace users
            shift.users.clear()
        else:
            shift = Shift(
                team_id=team.id,
                date=shift_date,
            )
            self.db.add(shift)

        if users:
            shift.users.extend(users)

        await self.db.commit()
        await self.db.refresh(shift)
        return shift

    async def add_user_to_shift(
        self,
        team: Team,
        shift_date: date,
        user: User
    ) -> Shift:
        """Add user to shift"""
        stmt = select(Shift).options(
            selectinload(Shift.users)
        ).where(
            (Shift.team_id == team.id) & (Shift.date == shift_date)
        )
        result = await self.db.execute(stmt)
        shift = result.scalars().first()

        if not shift:
            shift = Shift(
                team_id=team.id,
                date=shift_date,
            )
            self.db.add(shift)

        if user not in shift.users:
            shift.users.append(user)

        await self.db.commit()
        await self.db.refresh(shift)
        return shift

    async def remove_user_from_shift(
        self,
        team: Team,
        shift_date: date,
        user: User
    ) -> Shift | None:
        """Remove user from shift"""
        stmt = select(Shift).options(
            selectinload(Shift.users)
        ).where(
            (Shift.team_id == team.id) & (Shift.date == shift_date)
        )
        result = await self.db.execute(stmt)
        shift = result.scalars().first()

        if shift and user in shift.users:
            shift.users.remove(user)
            await self.db.commit()
            await self.db.refresh(shift)

        return shift

    async def get_shift(self, team: Team, shift_date: date) -> Shift | None:
        """Get shift for a date"""
        stmt = select(Shift).options(
            selectinload(Shift.users)
        ).where(
            (Shift.team_id == team.id) & (Shift.date == shift_date)
        )
        result = await self.db.execute(stmt)
        return result.scalars().first()

    async def get_shifts_by_date_range(
        self,
        team: Team,
        start_date: date,
        end_date: date
    ) -> list[Shift]:
        """Get shifts for a date range"""
        stmt = select(Shift).options(
            selectinload(Shift.users)
        ).where(
            (Shift.team_id == team.id) &
            (Shift.date >= start_date) &
            (Shift.date <= end_date)
        ).order_by(Shift.date)
        result = await self.db.execute(stmt)
        return result.scalars().all()

    async def clear_shift(self, team: Team, shift_date: date) -> bool:
        """Clear shift for a date"""
        stmt = select(Shift).where(
            (Shift.team_id == team.id) & (Shift.date == shift_date)
        )
        result = await self.db.execute(stmt)
        shift = result.scalars().first()

        if shift:
            await self.db.delete(shift)
            await self.db.commit()
            return True

        return False

    async def get_today_shift(self, team: Team, today: date) -> list[User]:
        """Get today's shift members"""
        shift = await self.get_shift(team, today)
        return shift.users if shift else []

    async def check_user_shift_conflict(
        self,
        user: User,
        shift_date: date
    ) -> dict | None:
        """Check if user is already assigned to a shift on this date

        Returns: dict with conflict info if conflict exists, None otherwise
        Example: {"user_id": 1, "date": "2024-01-15", "team_name": "Engineering"}
        """
        stmt = select(Shift).options(
            selectinload(Shift.users),
            selectinload(Shift.team)
        ).where(
            Shift.date == shift_date
        )
        result = await self.db.execute(stmt)
        shifts = result.scalars().all()

        # Check all shifts on this date to see if user is already assigned
        for shift in shifts:
            if any(u.id == user.id for u in shift.users):
                return {
                    "user_id": user.id,
                    "date": str(shift_date),
                    "team_id": shift.team_id,
                    "team_name": shift.team.name if shift.team else "Unknown"
                }
        return None
