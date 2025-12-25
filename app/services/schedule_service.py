from datetime import date
import logging
from sqlalchemy import select
from app.models import Schedule, Team, User
from app.repositories import ScheduleRepository, GoogleCalendarRepository

logger = logging.getLogger(__name__)


class ScheduleService:
    def __init__(self, schedule_repo: ScheduleRepository, google_calendar_repo: GoogleCalendarRepository = None):
        self.schedule_repo = schedule_repo
        self.google_calendar_repo = google_calendar_repo

    async def set_duty(
        self,
        team_id: int,
        user_id: int | None,
        duty_date: date
    ) -> Schedule:
        """Set or update duty for a date"""
        schedule = await self.schedule_repo.get_by_team_and_date(team_id, duty_date)

        if schedule:
            schedule = await self.schedule_repo.update(schedule.id, {
                'user_id': user_id
            })
        else:
            schedule = await self.schedule_repo.create({
                'team_id': team_id,
                'user_id': user_id,
                'date': duty_date,
            })

        # Sync to Google Calendar if available
        await self._sync_schedule_to_calendar(schedule)

        return schedule

    async def get_duty(self, team_id: int, duty_date: date) -> Schedule | None:
        """Get duty for a specific date"""
        return await self.schedule_repo.get_by_team_and_date(team_id, duty_date)

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
        """Get today's duty person"""
        schedule = await self.get_duty(team_id, today)
        return schedule.user if schedule else None

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

        schedule = await self.schedule_repo.update(schedule_id, update_data)

        # Sync to Google Calendar if available
        await self._sync_schedule_to_calendar(schedule)

        return schedule

    async def _sync_schedule_to_calendar(self, schedule: Schedule) -> None:
        """Sync schedule to Google Calendar if integration is available"""
        if not self.google_calendar_repo or not schedule or not schedule.user or not schedule.team:
            return

        try:
            from app.services.google_calendar_service import GoogleCalendarService

            # Get workspace from team
            workspace_id = schedule.team.workspace_id

            # Check if Google Calendar is configured for this workspace
            integration = await self.google_calendar_repo.get_by_workspace(workspace_id)
            if not integration or not integration.is_active:
                return

            # Sync to calendar
            google_service = GoogleCalendarService(self.google_calendar_repo)
            await google_service.sync_schedule_to_calendar(integration, schedule.team, schedule)

        except Exception as e:
            logger.error(f"Error syncing schedule to Google Calendar: {e}")
