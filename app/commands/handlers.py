from datetime import date, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from app.commands.parser import CommandParser, DateParser, CommandError, DateRange
from app.services.user_service import UserService
from app.services.team_service import TeamService
from app.services.schedule_service import ScheduleService
from app.services.shift_service import ShiftService
from app.services.escalation_service import EscalationService
from app.models import Team, User


class CommandHandler:
    """Handle all bot commands"""

    def __init__(self, db: AsyncSession, workspace_id: int = 1):
        self.db = db
        self.workspace_id = workspace_id
        self.user_service = UserService(db)
        self.team_service = TeamService(db)
        self.schedule_service = ScheduleService(db)
        self.shift_service = ShiftService(db)
        self.escalation_service = EscalationService(db)

    async def help(self) -> str:
        """Return full list of commands"""
        return """*Available Commands*

*📅 Duty*
• `/duty` - Show all on-duty today
• `/duty <team>` - Mention team's duty person/shift

*👥 Team Management*
• `/team list` - List all teams
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
        if today is None:
            today = date.today()

        teams = await self.team_service.get_all_teams(self.workspace_id)

        if not teams:
            return "No teams configured."

        result = []
        for team in teams:
            if team.has_shifts:
                shift = await self.shift_service.get_today_shift(team, today)
                if shift:
                    names = ", ".join([u.display_name for u in shift])
                    result.append(f"**{team.display_name}**: {names}")
                else:
                    result.append(f"**{team.display_name}**: не назначен")
            else:
                user = await self.schedule_service.get_today_duty(team, today)
                if user:
                    result.append(f"**{team.display_name}**: {user.display_name}")
                else:
                    result.append(f"**{team.display_name}**: не назначен")

        return "\n".join(result)

    async def mention_duty(self, team_name: str, today: date = None) -> str:
        """Mention today's duty person/shift"""
        if today is None:
            today = date.today()

        team = await self.team_service.get_team_by_name(self.workspace_id, team_name)
        if not team:
            raise CommandError(f"Team not found: {team_name}")

        if team.has_shifts:
            shift = await self.shift_service.get_today_shift(team, today)
            if not shift:
                raise CommandError(f"No shift assigned for {team.display_name} today")
            mentions = " ".join([f"@{u.telegram_username or u.slack_user_id}" for u in shift])
            return f"Today's shift for {team.display_name}: {mentions}"
        else:
            user = await self.schedule_service.get_today_duty(team, today)
            if not user:
                raise CommandError(f"No duty assigned for {team.display_name} today")
            mention = f"@{user.telegram_username or user.slack_user_id}"
            return f"Today's duty for {team.display_name}: {mention}"

    # ==================== Team Commands ====================

    async def team_list(self) -> str:
        """List all teams"""
        teams = await self.team_service.get_all_teams(self.workspace_id)

        if not teams:
            return "No teams configured."

        result = []
        for team in teams:
            lead_name = team.team_lead_user.display_name if team.team_lead_user else "None"
            mode = " (shifts)" if team.has_shifts else ""
            result.append(f"• {team.display_name} (id: {team.name}){mode} - Lead: {lead_name}")

        return "\n".join(result)

    async def team_info(self, team_name: str) -> str:
        """Show team composition"""
        team = await self.team_service.get_team_by_name(self.workspace_id, team_name)
        if not team:
            raise CommandError(f"Team not found: {team_name}")

        lead = team.team_lead_user.display_name if team.team_lead_user else "None"
        mode = "shifts" if team.has_shifts else "duty"
        members_str = ", ".join([m.display_name for m in team.members]) if team.members else "No members"

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

        team = await self.team_service.update_team(team, name=new_name)
        return f"Team renamed to: {new_name}"

    async def team_edit_display(self, team_name: str, new_display: str) -> str:
        """Change display name"""
        team = await self.team_service.get_team_by_name(self.workspace_id, team_name)
        if not team:
            raise CommandError(f"Team not found: {team_name}")

        team = await self.team_service.update_team(team, display_name=new_display)
        return f"Display name changed to: {new_display}"

    async def team_edit_shifts(self, team_name: str, enabled: bool) -> str:
        """Enable/disable shift mode"""
        team = await self.team_service.get_team_by_name(self.workspace_id, team_name)
        if not team:
            raise CommandError(f"Team not found: {team_name}")

        team = await self.team_service.update_team(team, has_shifts=enabled)
        mode = "enabled" if enabled else "disabled"
        return f"Shift mode {mode} for {team.display_name}"

    async def team_set_lead(self, team_name: str, user: User) -> str:
        """Set team lead"""
        team = await self.team_service.get_team_by_name(self.workspace_id, team_name)
        if not team:
            raise CommandError(f"Team not found: {team_name}")

        team = await self.team_service.set_team_lead(team, user)
        return f"Team lead set to {user.display_name} for {team.display_name}"

    async def team_add_member(self, team_name: str, user: User) -> str:
        """Add team member"""
        team = await self.team_service.get_team_by_name(self.workspace_id, team_name)
        if not team:
            raise CommandError(f"Team not found: {team_name}")

        team = await self.team_service.add_member(team, user)
        return f"{user.display_name} added to {team.display_name}"

    async def team_remove_member(self, team_name: str, user: User) -> str:
        """Remove team member"""
        team = await self.team_service.get_team_by_name(self.workspace_id, team_name)
        if not team:
            raise CommandError(f"Team not found: {team_name}")

        if user not in team.members:
            raise CommandError(f"{user.display_name} is not in {team.display_name}")

        team = await self.team_service.remove_member(team, user)
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

        await self.team_service.remove_member(from_team, user)
        await self.team_service.add_member(to_team, user)

        return f"{user.display_name} moved from {from_team.display_name} to {to_team.display_name}"

    async def team_delete(self, team_name: str) -> str:
        """Delete team"""
        team = await self.team_service.get_team_by_name(self.workspace_id, team_name)
        if not team:
            raise CommandError(f"Team not found: {team_name}")

        await self.team_service.delete_team(team)
        return f"Team {team.display_name} deleted"

    # ==================== Schedule Commands ====================

    async def schedule_show(self, team_name: str, period: str = "week", today: date = None) -> str:
        """Show schedule"""
        if today is None:
            today = date.today()

        team = await self.team_service.get_team_by_name(self.workspace_id, team_name)
        if not team:
            raise CommandError(f"Team not found: {team_name}")

        if team.has_shifts:
            raise CommandError(f"{team.display_name} uses shift mode, use /shift instead")

        # Determine date range
        if period == "week":
            date_range = CommandParser.get_current_week_dates(today)
        elif period == "next":
            date_range = CommandParser.get_next_week_dates(today)
        else:
            date_range = DateParser.get_month_dates(period, today)

        schedules = await self.schedule_service.get_duties_by_date_range(
            team, date_range.start, date_range.end
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
        today: date = None
    ) -> str:
        """Set duty for date range"""
        if today is None:
            today = date.today()

        team = await self.team_service.get_team_by_name(self.workspace_id, team_name)
        if not team:
            raise CommandError(f"Team not found: {team_name}")

        if team.has_shifts:
            raise CommandError(f"{team.display_name} uses shift mode, use /shift instead")

        date_range = DateParser.parse_date_range(date_range_str, today)

        current = date_range.start
        count = 0
        while current <= date_range.end:
            await self.schedule_service.set_duty(team, user, current)
            count += 1
            current += timedelta(days=1)

        return f"Duty set for {user.display_name} for {count} day(s)"

    async def schedule_clear(
        self,
        team_name: str,
        date_range_str: str,
        today: date = None
    ) -> str:
        """Clear duty for date range"""
        if today is None:
            today = date.today()

        team = await self.team_service.get_team_by_name(self.workspace_id, team_name)
        if not team:
            raise CommandError(f"Team not found: {team_name}")

        date_range = DateParser.parse_date_range(date_range_str, today)

        current = date_range.start
        count = 0
        while current <= date_range.end:
            if await self.schedule_service.clear_duty(team, current):
                count += 1
            current += timedelta(days=1)

        return f"Duty cleared for {count} day(s)"

    # ==================== Shift Commands ====================

    async def shift_show(self, team_name: str, period: str = "week", today: date = None) -> str:
        """Show shifts"""
        if today is None:
            today = date.today()

        team = await self.team_service.get_team_by_name(self.workspace_id, team_name)
        if not team:
            raise CommandError(f"Team not found: {team_name}")

        if not team.has_shifts:
            raise CommandError(f"{team.display_name} uses duty mode, use /schedule instead")

        # Determine date range
        if period == "week":
            date_range = CommandParser.get_current_week_dates(today)
        elif period == "next":
            date_range = CommandParser.get_next_week_dates(today)
        else:
            date_range = DateParser.get_month_dates(period, today)

        shifts = await self.shift_service.get_shifts_by_date_range(
            team, date_range.start, date_range.end
        )

        if not shifts:
            return f"No shifts assigned for {team.display_name} in this period"

        result = []
        for shift in shifts:
            names = ", ".join([u.display_name for u in shift.users]) if shift.users else "не назначена"
            result.append(f"{shift.date.strftime('%a %d.%m')}: {names}")

        return f"**{team.display_name}**\n" + "\n".join(result)

    async def shift_set(
        self,
        team_name: str,
        date_range_str: str,
        users: list[User],
        today: date = None
    ) -> str:
        """Set shift for date range"""
        if today is None:
            today = date.today()

        team = await self.team_service.get_team_by_name(self.workspace_id, team_name)
        if not team:
            raise CommandError(f"Team not found: {team_name}")

        if not team.has_shifts:
            raise CommandError(f"{team.display_name} uses duty mode, use /schedule instead")

        date_range = DateParser.parse_date_range(date_range_str, today)

        current = date_range.start
        count = 0
        while current <= date_range.end:
            await self.shift_service.create_shift(team, current, users)
            count += 1
            current += timedelta(days=1)

        names = ", ".join([u.display_name for u in users])
        return f"Shift set for {names} for {count} day(s)"

    async def shift_add_user(
        self,
        team_name: str,
        shift_date_str: str,
        user: User,
        today: date = None
    ) -> str:
        """Add user to shift"""
        if today is None:
            today = date.today()

        team = await self.team_service.get_team_by_name(self.workspace_id, team_name)
        if not team:
            raise CommandError(f"Team not found: {team_name}")

        shift_date = DateParser.parse_date_string(shift_date_str, today)
        await self.shift_service.add_user_to_shift(team, shift_date, user)

        return f"{user.display_name} added to shift on {shift_date}"

    async def shift_remove_user(
        self,
        team_name: str,
        shift_date_str: str,
        user: User,
        today: date = None
    ) -> str:
        """Remove user from shift"""
        if today is None:
            today = date.today()

        team = await self.team_service.get_team_by_name(self.workspace_id, team_name)
        if not team:
            raise CommandError(f"Team not found: {team_name}")

        shift_date = DateParser.parse_date_string(shift_date_str, today)
        await self.shift_service.remove_user_from_shift(team, shift_date, user)

        return f"{user.display_name} removed from shift on {shift_date}"

    async def shift_clear(
        self,
        team_name: str,
        date_range_str: str,
        today: date = None
    ) -> str:
        """Clear shifts for date range"""
        if today is None:
            today = date.today()

        team = await self.team_service.get_team_by_name(self.workspace_id, team_name)
        if not team:
            raise CommandError(f"Team not found: {team_name}")

        date_range = DateParser.parse_date_range(date_range_str, today)

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
