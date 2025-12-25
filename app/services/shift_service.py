from datetime import date
import logging
from app.models import Shift, Team, User
from app.repositories import ShiftRepository, GoogleCalendarRepository

logger = logging.getLogger(__name__)


class ShiftService:
    def __init__(self, shift_repo: ShiftRepository, google_calendar_repo: GoogleCalendarRepository = None):
        self.shift_repo = shift_repo
        self.google_calendar_repo = google_calendar_repo

    async def create_shift(
        self,
        team: Team,
        shift_date: date,
        users: list[User] | None = None,
        commit: bool = True
    ) -> Shift:
        """Create or update shift for a date"""
        shift = await self.shift_repo.create_or_update_shift(team.id, shift_date, users)

        # Sync to Google Calendar if available
        await self._sync_shift_to_calendar(shift, team)

        return shift
        return await self.shift_repo.create_or_update_shift(team.id, shift_date, users, commit=commit)

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
        shift_date: date,
        workspace_id: int = None
    ) -> dict | None:
        """Check if user is already assigned to a shift on this date (optionally filtered by workspace)

        Returns: dict with conflict info if conflict exists, None otherwise
        Example: {"user_id": 1, "date": "2024-01-15", "team_name": "Engineering"}
        """
        shifts = await self.shift_repo.list_by_user_and_date_range(user.id, shift_date, shift_date, workspace_id)

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

    async def _sync_shift_to_calendar(self, shift: Shift, team: Team) -> None:
        """Sync shift to Google Calendar if integration is available"""
        if not self.google_calendar_repo or not shift or not team:
            return

        try:
            from app.services.google_calendar_service import GoogleCalendarService

            # Get workspace from team
            workspace_id = team.workspace_id

            # Check if Google Calendar is configured for this workspace
            integration = await self.google_calendar_repo.get_by_workspace(workspace_id)
            if not integration or not integration.is_active:
                return

            # Sync to calendar
            google_service = GoogleCalendarService(self.google_calendar_repo)
            await google_service.sync_shift_to_calendar(integration, team, shift)

        except Exception as e:
            logger.error(f"Error syncing shift to Google Calendar: {e}")
