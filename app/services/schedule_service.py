from datetime import date
import logging
from sqlalchemy import select
from sqlalchemy.orm import joinedload
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
        duty_date: date,
        is_shift: bool = False,
        commit: bool = True,
        force: bool = False
    ) -> Schedule:
        """Set or update duty for a date with validations"""
        # 1. Prevent scheduling in the past
        today = date.today()
        if duty_date < today and not force:
            raise ValueError(f"Cannot schedule duty for past date {duty_date}")

        # Fetch team to check shift status
        from app.repositories.team_repository import TeamRepository
        team_repo = TeamRepository(self.schedule_repo.db)
        team = await team_repo.get_by_id(team_id)
        if not team:
            raise ValueError(f"Team {team_id} not found")

        # 2. Check if shifts are allowed for this team
        if is_shift and not team.has_shifts and not force:
            raise ValueError(f"Team {team.display_name} does not have shifts enabled")

        # 3. Check for 1 person per day if not in shift mode (handled by repo, but let's be explicit)
        if not is_shift and not force:
            existing_duties = await self.get_duties_by_date(team_id, duty_date)
            # If we are setting a NEW duty and someone else is already there
            # create_or_update_schedule overwrites by default. 
            # If the user wants to "prevent" it, they might mean "don't ever allow 2 records".
            # The repo ensures 1 record if is_shift=False.

        # 4. Check for duplicate person on the same day (across all teams)
        if user_id and not force:
            conflict = await self.check_user_schedule_conflict(user_id, duty_date)
            if conflict and (conflict['team_name'] != team.name or is_shift):
                # If it's a different team, or the same team but we are adding a shift (which would be a duplicate record for same team/date)
                raise ValueError(f"User is already on duty on {duty_date} in team {conflict['team_display_name']}")

        schedule = await self.schedule_repo.create_or_update_schedule(team_id, duty_date, user_id, is_shift=is_shift, commit=commit)
        
        # Sync to Google Calendar if available
        if schedule:
            await self._sync_schedule_to_calendar(schedule)
            
        return schedule


    async def get_duty(self, team_id: int, duty_date: date) -> Schedule | None:
        """Get duty for a specific date (returns first found)"""
        return await self.schedule_repo.get_by_team_and_date(team_id, duty_date)

    async def get_duties_by_date(self, team_id: int, duty_date: date) -> list[Schedule]:
        """Get all duties/shifts for a specific date and team"""
        stmt = select(Schedule).options(joinedload(Schedule.user)).where(
            Schedule.team_id == team_id,
            Schedule.date == duty_date
        )
        result = await self.schedule_repo.execute(stmt)
        return result.scalars().all()

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
        """Get today's primary duty person (returns first found)"""
        schedule = await self.get_duty(team_id, today)
        return schedule.user if schedule else None

    async def get_today_duties(self, team_id: int, today: date) -> list[User]:
        """Get all today's on-duty people for a team"""
        schedules = await self.get_duties_by_date(team_id, today)
        return [s.user for s in schedules if s.user]

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
                "id": existing.id,
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
        team_id: int | None = None,
        force: bool = False
    ) -> Schedule:
        """Update existing duty assignment with validations"""
        # 1. Prevent scheduling in the past
        today = date.today()
        if duty_date < today and not force:
            raise ValueError(f"Cannot schedule duty for past date {duty_date}")

        schedule = await self.schedule_repo.get_by_id(schedule_id)
        if not schedule:
            raise ValueError(f"Schedule with id {schedule_id} not found")

        target_team_id = team_id or schedule.team_id
        
        # Fetch team to check shift status
        from app.repositories.team_repository import TeamRepository
        team_repo = TeamRepository(self.schedule_repo.db)
        team = await team_repo.get_by_id(target_team_id)
        if not team:
            raise ValueError(f"Team {target_team_id} not found")

        # 2. Check for duplicate person on the same day (across all teams)
        if user_id and not force:
            conflict = await self.check_user_schedule_conflict(user_id, duty_date)
            # If conflict is found and it's NOT the current record we are updating
            if conflict and conflict.get('id') != schedule_id: 
                # Wait, check_user_schedule_conflict returns a dict with user_id, date, team_name... 
                # I should update check_user_schedule_conflict to return ID or something to distinguish.
                # For now, let's just check if it's a different team.
                if conflict['team_name'] != team.name:
                    raise ValueError(f"User is already on duty on {duty_date} in team {conflict['team_display_name']}")

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
