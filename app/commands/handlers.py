from datetime import date, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from app.commands.parser import CommandParser, DateParser, CommandError, DateRange
from app.services.user_service import UserService
from app.services.team_service import TeamService
from app.services.schedule_service import ScheduleService
from app.services.escalation_service import EscalationService
from app.services.admin_service import AdminService
from app.services.rotation_service import RotationService
from app.services.incident_service import IncidentService
from app.services.metrics_service import MetricsService
from app.repositories import (
    UserRepository, TeamRepository, ScheduleRepository,
    EscalationRepository, EscalationEventRepository, AdminLogRepository, RotationConfigRepository,
    IncidentRepository
)
from app.models import Team, User
from app.config import get_settings


class CommandHandler:
    """Handle all bot commands"""

    def __init__(self, db: AsyncSession, workspace_id: int = 1):
        self.db = db
        self.workspace_id = workspace_id

        # Initialize repositories
        self.user_repo = UserRepository(db)
        self.team_repo = TeamRepository(db)
        self.schedule_repo = ScheduleRepository(db)
        self.escalation_repo = EscalationRepository(db)
        self.escalation_event_repo = EscalationEventRepository(db)
        self.admin_log_repo = AdminLogRepository(db)
        self.rotation_config_repo = RotationConfigRepository(db)
        self.incident_repo = IncidentRepository(db)

        # Initialize services with repositories
        self.user_service = UserService(self.user_repo, self.admin_log_repo)
        self.team_service = TeamService(self.team_repo)
        self.schedule_service = ScheduleService(self.schedule_repo)
        self.escalation_service = EscalationService(self.escalation_repo, self.escalation_event_repo)
        self.admin_service = AdminService(self.admin_log_repo, self.user_repo)
        self.rotation_service = RotationService(self.rotation_config_repo, self.schedule_repo, self.user_repo)
        self.incident_service = IncidentService(self.incident_repo)
        self.metrics_service = MetricsService(self.incident_repo)
        self.settings = get_settings()

    def _get_today(self, today: date = None) -> date:
        """Get today's date in the configured timezone"""
        if today is None:
            from datetime import datetime
            from zoneinfo import ZoneInfo
            tz = ZoneInfo(self.settings.timezone)
            today = datetime.now(tz).date()
        return today

    async def help(self) -> str:
        """Return full list of commands"""
        return """*Available Commands*

*📅 Duty*
• `/duty` - Show all on-duty today
• `/duty <team>` - Mention team's duty person/shift

*👥 Team Management*
• `/team` - List all teams
• `/team <name>` - Show team info
• `/team add <name> "<display_name>"` - Create team
• `/team add <name> "<display_name>" --shifts` - Create with shifts
• `/team edit <name> --name <new_name>` - Rename team
• `/team edit <name> --display "<new_name>"` - Change display name
• `/team edit <name> --shifts` - Enable shifts
• `/team edit <name> --no-shifts` - Disable shifts
• `/team lead <team> @user` - Set team lead
• `/team add-member <team> @user` - Add member
• `/team remove-member <team> @user` - Remove member
• `/team move @user <from_team> <to_team>` - Move member
• `/team delete <team>` - Delete team

*🗓 Scheduling (without shifts)*
• `/schedule <team>` - Show current week
• `/schedule <team> next` - Show next week
• `/schedule <team> <month>` - Show month
• `/schedule <team> set <date> @user` - Set duty
• `/schedule <team> set <date>-<date> @user` - Set range
• `/schedule <team> clear <date>` - Clear duty
• `/schedule <team> clear <date>-<date>` - Clear range

*🔁 Auto-rotation*
• `/schedule <team> rotate` - Show rotation status
• `/schedule <team> rotate enable @user1 @user2 ...` - Enable rotation with order
• `/schedule <team> rotate assign <date>` - Auto-assign next person
• `/schedule <team> rotate disable` - Disable rotation

*🔄 Shifts (with shifts)*
• `/shift <team>` - Show current week
• `/shift <team> next` - Show next week
• `/shift <team> <month>` - Show month
• `/shift <team> set <date> @user1 @user2 ...` - Set shift
• `/shift <team> set <date>-<date> @user1 @user2 ...` - Set range
• `/shift <team> add <date> @user` - Add to shift
• `/shift <team> remove <date> @user` - Remove from shift
• `/shift <team> clear <date>` - Clear shift
• `/shift <team> clear <date>-<date>` - Clear range

*🚨 Escalation*
• `/escalation` - Show escalation settings
• `/escalation cto @user` - Set CTO
• `/escalate <team>` - Escalate to team lead
• `/escalate level2` - Escalate to CTO
• `/escalate ack` - Acknowledge escalation

*Date Format:*
• `DD.MM`, `DD.MM.YYYY`
• Month name (e.g., `december`)
• `DD.MM-DD.MM` for ranges"""

    # ==================== Duty Commands ====================

    async def duty_today(self, today: date = None) -> str:
        """Show all on-duty people today"""
        today = self._get_today(today)

        teams = await self.team_service.get_all_teams(self.workspace_id)

        if not teams:
            return "No teams configured."

        result = []
        for team in teams:
            users = await self.schedule_service.get_today_duties(team.id, today)
            if users:
                names = ", ".join([u.display_name for u in users])
                result.append(f"**{team.display_name}**: {names}")
            else:
                result.append(f"**{team.display_name}**: не назначен")

        return "\n".join(result)

    async def mention_duty(self, team_name: str, today: date = None) -> str:
        """Mention today's duty person/shift"""
        today = self._get_today(today)

        team = await self.team_service.get_team_by_name(self.workspace_id, team_name)
        if not team:
            raise CommandError(f"Team not found: {team_name}")

        users = await self.schedule_service.get_today_duties(team.id, today)
        if not users:
            raise CommandError(f"No duty assigned for {team.display_name} today")
        
        mentions = " ".join([f"@{u.telegram_username or u.slack_user_id}" for u in users])
        return f"Today's duty for {team.display_name}: {mentions}"

    # ==================== Team Commands ====================

    async def team_list(self) -> str:
        """List all teams"""
        teams = await self.team_service.get_all_teams(self.workspace_id)

        if not teams:
            return "No teams configured."

        def get_full_name(user):
            parts = []
            if user.first_name:
                parts.append(user.first_name)
            if user.last_name:
                parts.append(user.last_name)
            return " ".join(parts) if parts else user.display_name

        result = []
        for team in teams:
            lead_name = get_full_name(team.team_lead_user) if team.team_lead_user else "None"
            mode = " (shifts)" if team.has_shifts else ""
            result.append(f"• {team.display_name} (id: {team.name}){mode} - Lead: {lead_name}")

        return "\n".join(result)

    async def team_info(self, team_name: str) -> str:
        """Show team composition"""
        team = await self.team_service.get_team_by_name(self.workspace_id, team_name)
        if not team:
            raise CommandError(f"Team not found: {team_name}")

        def get_full_name(user):
            parts = []
            if user.first_name:
                parts.append(user.first_name)
            if user.last_name:
                parts.append(user.last_name)
            return " ".join(parts) if parts else user.display_name

        lead = get_full_name(team.team_lead_user) if team.team_lead_user else "None"
        mode = "shifts" if team.has_shifts else "duty"
        members_str = ", ".join([get_full_name(m) for m in team.members]) if team.members else "No members"

        return f"""**{team.display_name}**
Mode: {mode}
Lead: {lead}
Members: {members_str}"""

    async def team_add(self, name: str, display_name: str, has_shifts: bool = False) -> str:
        """Create team"""
        existing = await self.team_service.get_team_by_name(self.workspace_id, name)
        if existing:
            raise CommandError(f"Team already exists: {name}")

        team = await self.team_service.create_team(self.workspace_id, name, display_name, has_shifts)
        return f"Team created: {team.display_name}"

    async def team_edit_name(self, team_name: str, new_name: str) -> str:
        """Rename team identifier"""
        team = await self.team_service.get_team_by_name(self.workspace_id, team_name)
        if not team:
            raise CommandError(f"Team not found: {team_name}")

        existing = await self.team_service.get_team_by_name(self.workspace_id, new_name)
        if existing and existing.id != team.id:
            raise CommandError(f"Team already exists: {new_name}")

        team = await self.team_service.update_team(team.id, name=new_name)
        return f"Team renamed to: {new_name}"

    async def team_edit_display(self, team_name: str, new_display: str) -> str:
        """Change display name"""
        team = await self.team_service.get_team_by_name(self.workspace_id, team_name)
        if not team:
            raise CommandError(f"Team not found: {team_name}")

        team = await self.team_service.update_team(team.id, display_name=new_display)
        return f"Display name changed to: {new_display}"

    async def team_edit_shifts(self, team_name: str, enabled: bool) -> str:
        """Enable/disable shift mode"""
        team = await self.team_service.get_team_by_name(self.workspace_id, team_name)
        if not team:
            raise CommandError(f"Team not found: {team_name}")

        team = await self.team_service.update_team(team.id, has_shifts=enabled)
        mode = "enabled" if enabled else "disabled"
        return f"Shift mode {mode} for {team.display_name}"

    async def team_set_lead(self, team_name: str, user: User) -> str:
        """Set team lead"""
        team = await self.team_service.get_team_by_name(self.workspace_id, team_name)
        if not team:
            raise CommandError(f"Team not found: {team_name}")

        team = await self.team_service.set_team_lead(team.id, user.id)
        return f"Team lead set to {user.display_name} for {team.display_name}"

    async def team_add_member(self, team_name: str, user: User) -> str:
        """Add team member"""
        team = await self.team_service.get_team_by_name(self.workspace_id, team_name)
        if not team:
            raise CommandError(f"Team not found: {team_name}")

        team = await self.team_service.add_member(team.id, user)
        return f"{user.display_name} added to {team.display_name}"

    async def team_remove_member(self, team_name: str, user: User) -> str:
        """Remove team member"""
        team = await self.team_service.get_team_by_name(self.workspace_id, team_name)
        if not team:
            raise CommandError(f"Team not found: {team_name}")

        if user not in team.members:
            raise CommandError(f"{user.display_name} is not in {team.display_name}")

        team = await self.team_service.remove_member(team.id, user)
        return f"{user.display_name} removed from {team.display_name}"

    async def team_move_member(
        self,
        user: User,
        from_team_name: str,
        to_team_name: str
    ) -> str:
        """Move member between teams"""
        from_team = await self.team_service.get_team_by_name(self.workspace_id, from_team_name)
        if not from_team:
            raise CommandError(f"Team not found: {from_team_name}")

        to_team = await self.team_service.get_team_by_name(self.workspace_id, to_team_name)
        if not to_team:
            raise CommandError(f"Team not found: {to_team_name}")

        if user not in from_team.members:
            raise CommandError(f"{user.display_name} is not in {from_team.display_name}")

        await self.team_service.remove_member(from_team.id, user)
        await self.team_service.add_member(to_team.id, user)

        return f"{user.display_name} moved from {from_team.display_name} to {to_team.display_name}"

    async def team_delete(self, team_name: str) -> str:
        """Delete team"""
        team = await self.team_service.get_team_by_name(self.workspace_id, team_name)
        if not team:
            raise CommandError(f"Team not found: {team_name}")

        await self.team_service.delete_team(team.id)
        return f"Team {team.display_name} deleted"

    # ==================== Schedule Commands ====================

    async def schedule_show(self, team_name: str, period: str = "week", today: date = None) -> str:
        """Show schedule"""
        today = self._get_today(today)

        team = await self.team_service.get_team_by_name(self.workspace_id, team_name)
        if not team:
            raise CommandError(f"Team not found: {team_name}")

        if team.has_shifts:
            raise CommandError(f"{team.display_name} uses shift mode, use /shift instead")

        # Determine date range
        if period == "week":
            date_range = CommandParser.get_current_week_dates(today, self.settings.timezone)
        elif period == "next":
            date_range = CommandParser.get_next_week_dates(today, self.settings.timezone)
        else:
            date_range = DateParser.get_month_dates(period, today, self.settings.timezone)

        schedules = await self.schedule_service.get_duties_by_date_range(
            team.id, date_range.start, date_range.end
        )

        if not schedules:
            return f"No duties assigned for {team.display_name} in this period"

        result = []
        for schedule in schedules:
            name = schedule.user.display_name if schedule.user else "не назначен"
            result.append(f"{schedule.date.strftime('%a %d.%m')}: {name}")

        return f"**{team.display_name}**\n" + "\n".join(result)

    async def schedule_set(
        self,
        team_name: str,
        date_range_str: str,
        user: User,
        today: date = None,
        force: bool = False
    ) -> str:
        """Set duty for date range"""
        today = self._get_today(today)

        team = await self.team_service.get_team_by_name(self.workspace_id, team_name)
        if not team:
            raise CommandError(f"Team not found: {team_name}")

        if team.has_shifts:
            raise CommandError(f"{team.display_name} uses shift mode, use /shift instead")

        date_range = DateParser.parse_date_range(date_range_str, today, self.settings.timezone)

        # Check for conflicts
        conflicts = []
        current = date_range.start
        while current <= date_range.end:
            conflict = await self.schedule_service.check_user_schedule_conflict(user.id, current, self.workspace_id)
            if conflict:
                conflicts.append(conflict)
            current += timedelta(days=1)

        # Handle conflicts
        if conflicts and not force:
            conflict_info = "\n".join([
                f"  • {c['date']} - already scheduled in {c['team_display_name']}"
                for c in conflicts
            ])
            raise CommandError(
                f"⚠️ Scheduling conflicts detected:\n{conflict_info}\n"
                f"Use --force flag to override"
            )

        # Log conflict attempts
        if conflicts:
            await self.admin_service.log_action(
                workspace_id=self.workspace_id,
                admin_id=user.id,
                action="schedule_conflict_override",
                target_user_id=user.id,
                details={
                    "team_name": team.name,
                    "team_id": team.id,
                    "date_range": f"{date_range.start} to {date_range.end}",
                    "conflicts_count": len(conflicts),
                    "conflicts": conflicts
                }
            )

        current = date_range.start
        count = 0
        while current <= date_range.end:
            await self.schedule_service.set_duty(team.id, user.id, current)
            count += 1
            current += timedelta(days=1)

        result = f"Duty set for {user.display_name} for {count} day(s)"
        if conflicts:
            result += f"\n⚠️ Conflicts overridden for {len(conflicts)} date(s)"

        return result

    async def schedule_clear(
        self,
        team_name: str,
        date_range_str: str,
        today: date = None
    ) -> str:
        """Clear duty for date range"""
        today = self._get_today(today)

        team = await self.team_service.get_team_by_name(self.workspace_id, team_name)
        if not team:
            raise CommandError(f"Team not found: {team_name}")

        date_range = DateParser.parse_date_range(date_range_str, today, self.settings.timezone)

        current = date_range.start
        count = 0
        while current <= date_range.end:
            if await self.schedule_service.clear_duty(team.id, current):
                count += 1
            current += timedelta(days=1)

        return f"Duty cleared for {count} day(s)"

    # ==================== Shift Commands ====================

    async def shift_show(self, team_name: str, period: str = "week", today: date = None) -> str:
        """Show shifts"""
        today = self._get_today(today)

        team = await self.team_service.get_team_by_name(self.workspace_id, team_name)
        if not team:
            raise CommandError(f"Team not found: {team_name}")

        if not team.has_shifts:
            raise CommandError(f"{team.display_name} uses duty mode, use /schedule instead")

        # Determine date range
        if period == "week":
            date_range = CommandParser.get_current_week_dates(today, self.settings.timezone)
        elif period == "next":
            date_range = CommandParser.get_next_week_dates(today, self.settings.timezone)
        else:
            date_range = DateParser.get_month_dates(period, today, self.settings.timezone)

        schedules = await self.schedule_service.get_duties_by_date_range(
            team.id, date_range.start, date_range.end
        )

        if not schedules:
            return f"No shifts assigned for {team.display_name} in this period"

        # Group by date for display
        by_date = {}
        for s in schedules:
            if s.date not in by_date: by_date[s.date] = []
            by_date[s.date].append(s.user.display_name if s.user else "Unknown")

        result = []
        # Sort dates
        for d in sorted(by_date.keys()):
            names = ", ".join(by_date[d])
            result.append(f"{d.strftime('%a %d.%m')}: {names}")

        return f"**{team.display_name}** (Shifts)\n" + "\n".join(result)

    async def shift_set(
        self,
        team_name: str,
        date_range_str: str,
        users: list[User],
        today: date = None,
        force: bool = False
    ) -> str:
        """Set shift for date range"""
        today = self._get_today(today)

        team = await self.team_service.get_team_by_name(self.workspace_id, team_name)
        if not team:
            raise CommandError(f"Team not found: {team_name}")

        if not team.has_shifts:
            raise CommandError(f"{team.display_name} uses duty mode, use /schedule instead")

        date_range = DateParser.parse_date_range(date_range_str, today, self.settings.timezone)

        # In unified model, we just set the duties for each user
        # Note: Set duty for each day/user pair
        current = date_range.start
        count = 0
        while current <= date_range.end:
            # First clear existing for these dates if needed? 
            # Or just replace? For shifts, we probably want to replace everyone.
            # actually set_duty with is_shift=True will append if not exists.
            # If we want to fully "SET" the shift to exactly these users, we should clear first.
            await self.schedule_repo.delete_by_team_and_date(team.id, current)
            
            for user in users:
                await self.schedule_service.set_duty(team.id, user.id, current, is_shift=True)
            count += 1
            current += timedelta(days=1)

        names = ", ".join([u.display_name for u in users])
        return f"Shift set for {names} for {count} day(s)"

    async def shift_add_user(
        self,
        team_name: str,
        shift_date_str: str,
        user: User,
        today: date = None,
        force: bool = False
    ) -> str:
        """Add user to shift"""
        today = self._get_today(today)

        team = await self.team_service.get_team_by_name(self.workspace_id, team_name)
        if not team:
            raise CommandError(f"Team not found: {team_name}")

        shift_date = DateParser.parse_date_string(shift_date_str, today, self.settings.timezone)
        
        await self.schedule_service.set_duty(team.id, user.id, shift_date, is_shift=True)

        return f"{user.display_name} added to shift on {shift_date}"

    async def shift_remove_user(
        self,
        team_name: str,
        shift_date_str: str,
        user: User,
        today: date = None
    ) -> str:
        """Remove user from shift"""
        today = self._get_today(today)

        team = await self.team_service.get_team_by_name(self.workspace_id, team_name)
        if not team:
            raise CommandError(f"Team not found: {team_name}")

        shift_date = DateParser.parse_date_string(shift_date_str, today, self.settings.timezone)
        
        # Remove specific user assignment
        stmt = select(Schedule).where(
            Schedule.team_id == team.id,
            Schedule.user_id == user.id,
            Schedule.date == shift_date
        )
        result = await self.db.execute(stmt)
        schedule = result.scalars().first()
        if schedule:
            await self.db.delete(schedule)
            await self.db.commit()

        return f"{user.display_name} removed from shift on {shift_date}"

    async def shift_clear(
        self,
        team_name: str,
        date_range_str: str,
        today: date = None
    ) -> str:
        """Clear shifts for date range"""
        today = self._get_today(today)

        team = await self.team_service.get_team_by_name(self.workspace_id, team_name)
        if not team:
            raise CommandError(f"Team not found: {team_name}")

        date_range = DateParser.parse_date_range(date_range_str, today, self.settings.timezone)

        current = date_range.start
        count = 0
        while current <= date_range.end:
            if await self.shift_service.clear_shift(team, current):
                count += 1
            current += timedelta(days=1)

        return f"Shifts cleared for {count} day(s)"

    # ==================== Escalation Commands ====================

    async def escalation_show(self) -> str:
        """Show escalation settings"""
        teams = await self.team_service.get_all_teams(self.workspace_id)
        cto = await self.escalation_service.get_cto(self.workspace_id)

        result = ["**Escalation Settings**"]
        result.append("Level 1 (Team Leads):")

        for team in teams:
            lead = team.team_lead_user.display_name if team.team_lead_user else "None"
            result.append(f"  • {team.display_name}: {lead}")

        result.append(f"Level 2 (CTO): {cto.display_name if cto else 'None'}")

        return "\n".join(result)

    async def escalation_set_cto(self, user: User) -> str:
        """Set CTO"""
        await self.escalation_service.set_cto(self.workspace_id, user)
        return f"CTO set to {user.display_name}"

    async def escalate_team(self, team_name: str) -> str:
        """Escalate to team lead"""
        team = await self.team_service.get_team_by_name(self.workspace_id, team_name)
        if not team:
            raise CommandError(f"Team not found: {team_name}")

        if not team.team_lead_user:
            raise CommandError(f"No team lead assigned for {team.display_name}")

        mention = f"@{team.team_lead_user.telegram_username or team.team_lead_user.slack_user_id}"
        return f"Escalating {team.display_name} issue to {mention}"

    async def escalate_cto(self) -> str:
        """Escalate to CTO"""
        cto = await self.escalation_service.get_cto(self.workspace_id)
        if not cto:
            raise CommandError("CTO not assigned")

        mention = f"@{cto.telegram_username or cto.slack_user_id}"
        return f"Escalating to CTO {mention}"

    # ==================== Rotation Commands ====================

    async def schedule_rotate_status(self, team_name: str) -> str:
        """Show rotation status for a team"""
        team = await self.team_service.get_team_by_name(self.workspace_id, team_name)
        if not team:
            raise CommandError(f"Team not found: {team_name}")

        if team.has_shifts:
            raise CommandError(f"{team.display_name} uses shift mode, rotation only works with duty mode")

        return await self.rotation_service.get_rotation_status(team)

    async def schedule_rotate_enable(
        self,
        team_name: str,
        users: list[User]
    ) -> str:
        """Enable rotation for a team with a specific order of members"""
        team = await self.team_service.get_team_by_name(self.workspace_id, team_name)
        if not team:
            raise CommandError(f"Team not found: {team_name}")

        if team.has_shifts:
            raise CommandError(f"{team.display_name} uses shift mode, rotation only works with duty mode")

        if not users:
            raise CommandError("At least one team member must be specified")

        # Extract user IDs
        user_ids = [u.id for u in users]

        # Enable rotation
        await self.rotation_service.enable_rotation(team, user_ids)

        user_names = ", ".join([u.display_name for u in users])
        return f"Rotation enabled for {team.display_name}\nOrder: {user_names}"

    async def schedule_rotate_assign(
        self,
        team_name: str,
        date_str: str,
        today: date = None
    ) -> str:
        """Automatically assign the next person in rotation to a date"""
        today = self._get_today(today)

        team = await self.team_service.get_team_by_name(self.workspace_id, team_name)
        if not team:
            raise CommandError(f"Team not found: {team_name}")

        if team.has_shifts:
            raise CommandError(f"{team.display_name} uses shift mode, rotation only works with duty mode")

        # Parse date
        date_range = DateParser.parse_date_range(date_str, today, self.settings.timezone)
        assignment_date = date_range.start

        # Assign rotation
        user, message = await self.rotation_service.assign_rotation(team, assignment_date)

        if not user:
            raise CommandError(message)

        return message

    async def schedule_rotate_disable(self, team_name: str) -> str:
        """Disable rotation for a team"""
        team = await self.team_service.get_team_by_name(self.workspace_id, team_name)
        if not team:
            raise CommandError(f"Team not found: {team_name}")

        if team.has_shifts:
            raise CommandError(f"{team.display_name} uses shift mode, rotation only works with duty mode")

        if await self.rotation_service.disable_rotation(team):
            return f"Rotation disabled for {team.display_name}"
        else:
            raise CommandError(f"No rotation configured for {team.display_name}")

    # ===============================
    # INCIDENT COMMANDS
    # ===============================

    async def incident_start(self, incident_name: str) -> str:
        """Start new incident"""
        if not incident_name:
            raise CommandError("Please provide incident name")

        incident = await self.incident_service.create_incident(self.workspace_id, incident_name)
        return f"🚨 Incident started: *{incident.name}* at {incident.start_time.strftime('%H:%M:%S')}"

    async def incident_stop(self) -> str:
        """Stop active incident"""
        active = await self.incident_service.get_active_incidents(self.workspace_id)
        if not active:
            raise CommandError("No active incidents")

        # Stop the first (most recent) active incident
        incident = active[0]
        completed = await self.incident_service.complete_incident(incident.id)

        if completed and completed.end_time:
            duration = (completed.end_time - completed.start_time).total_seconds()
            hours = int(duration // 3600)
            minutes = int((duration % 3600) // 60)
            duration_str = f"{hours}h {minutes}m" if hours > 0 else f"{minutes}m"
            return f"✅ Incident resolved: *{completed.name}* (Duration: {duration_str})"

        raise CommandError("Failed to complete incident")

    async def incident_list(self) -> str:
        """List active incidents"""
        active = await self.incident_service.get_active_incidents(self.workspace_id)
        if not active:
            return "No active incidents 😊"

        lines = ["🚨 *Active Incidents:*", ""]
        for inc in active:
            duration = (date.today() - inc.start_time.date()).days if inc.start_time else 0
            lines.append(f"• *{inc.name}* - started {inc.start_time.strftime('%d.%m %H:%M')}")

        return "\n".join(lines)

    async def incident_metrics(self, period: str = "week") -> str:
        """Get incident metrics"""
        if period not in ['week', 'month', 'quarter', 'year']:
            period = 'week'

        metrics = await self.metrics_service.calculate_metrics(self.workspace_id, period)

        mtr_hours = metrics['mtr'] // 3600
        mtr_minutes = (metrics['mtr'] % 3600) // 60
        avg_hours = metrics['averageIncidentDuration'] // 3600
        avg_minutes = (metrics['averageIncidentDuration'] % 3600) // 60

        return (
            f"📊 *Incident Metrics ({period.title()}):*\n"
            f"• MTR: {mtr_hours}h {mtr_minutes}m\n"
            f"• Days without incidents: {metrics['daysWithoutIncidents']}\n"
            f"• Total incidents: {metrics['totalIncidents']}\n"
            f"• Avg duration: {avg_hours}h {avg_minutes}m"
        )
