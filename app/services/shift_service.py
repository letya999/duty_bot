from datetime import date
from app.models import Shift, Team, User
from app.repositories import ShiftRepository


class ShiftService:
    def __init__(self, shift_repo: ShiftRepository):
        self.shift_repo = shift_repo

    async def create_shift(
        self,
        team: Team,
        shift_date: date,
        users: list[User] | None = None
    ) -> Shift:
        """Create or update shift for a date"""
        return await self.shift_repo.create_or_update_shift(team.id, shift_date, users)

    async def add_user_to_shift(
        self,
        team: Team,
        shift_date: date,
        user: User
    ) -> Shift:
        """Add user to shift"""
        return await self.shift_repo.add_user_to_shift(team.id, shift_date, user)

    async def remove_user_from_shift(
        self,
        team: Team,
        shift_date: date,
        user: User
    ) -> Shift | None:
        """Remove user from shift"""
        return await self.shift_repo.remove_user_from_shift(team.id, shift_date, user)

    async def get_shift(self, team: Team, shift_date: date) -> Shift | None:
        """Get shift for a date"""
        return await self.shift_repo.get_by_team_and_date(team.id, shift_date)

    async def get_shifts_by_date_range(
        self,
        team: Team,
        start_date: date,
        end_date: date
    ) -> list[Shift]:
        """Get shifts for a date range"""
        return await self.shift_repo.list_by_team_and_date_range(team.id, start_date, end_date)

    async def clear_shift(self, team: Team, shift_date: date) -> bool:
        """Clear shift for a date"""
        return await self.shift_repo.delete_by_team_and_date(team.id, shift_date)

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
        shifts = await self.shift_repo.list_by_user_and_date_range(user.id, shift_date, shift_date)

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
