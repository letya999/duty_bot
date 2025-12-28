import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import date
from sqlalchemy.ext.asyncio import AsyncSession
from app.commands.handlers import CommandHandler
from app.commands.parser import CommandError
from app.models import Team, User, Schedule, Incident
from app.handlers.telegram_handler import TelegramHandler, get_or_create_telegram_workspace


class TestCommandHandlerEdgeCases:
    """Test CommandHandler edge cases and error handling"""

    @pytest.fixture
    async def handler_setup(self, db_session: AsyncSession):
        """Setup handler with test data"""
        workspace_id = 1
        return CommandHandler(db_session, workspace_id), db_session

    @pytest.mark.asyncio
    async def test_team_not_found_error(self, handler_setup):
        """Test team not found error"""
        handler, db_session = handler_setup

        with pytest.raises(CommandError, match="Team not found"):
            await handler.team_info("nonexistent")

    @pytest.mark.asyncio
    async def test_team_edit_nonexistent_team(self, handler_setup):
        """Test editing non-existent team"""
        handler, db_session = handler_setup

        with pytest.raises(CommandError, match="Team not found"):
            await handler.team_edit_name("nonexistent", "newname")

    @pytest.mark.asyncio
    async def test_duplicate_team_add(self, db_session: AsyncSession):
        """Test adding duplicate team"""
        workspace_id = 1
        handler = CommandHandler(db_session, workspace_id)

        # Create first team
        await handler.team_add("backend", "Backend Team")

        # Try to add duplicate
        with pytest.raises(CommandError, match="Team already exists"):
            await handler.team_add("backend", "Another Backend")

    @pytest.mark.asyncio
    async def test_remove_nonexistent_member(self, db_session: AsyncSession):
        """Test removing non-existent member from team"""
        workspace_id = 1

        user = User(
            workspace_id=workspace_id,
            telegram_id=100,
            telegram_username="user1",
            first_name="User",
            last_name="One",
            display_name="User One"
        )
        db_session.add(user)
        await db_session.commit()
        await db_session.refresh(user)

        team = Team(
            workspace_id=workspace_id,
            name="backend",
            display_name="Backend Team"
        )
        db_session.add(team)
        await db_session.commit()

        handler = CommandHandler(db_session, workspace_id)

        with pytest.raises(CommandError, match="is not in"):
            await handler.team_remove_member("backend", user)

    @pytest.mark.asyncio
    async def test_move_member_from_nonexistent_team(self, db_session: AsyncSession):
        """Test moving member from non-existent team"""
        workspace_id = 1

        user = User(
            workspace_id=workspace_id,
            telegram_id=101,
            telegram_username="user1",
            first_name="User",
            last_name="One",
            display_name="User One"
        )
        db_session.add(user)
        await db_session.commit()
        await db_session.refresh(user)

        handler = CommandHandler(db_session, workspace_id)

        with pytest.raises(CommandError, match="Team not found"):
            await handler.team_move_member(user, "nonexistent", "target")

    @pytest.mark.asyncio
    async def test_escalate_to_nonexistent_team(self, handler_setup):
        """Test escalating to non-existent team"""
        handler, db_session = handler_setup

        with pytest.raises(CommandError, match="Team not found"):
            await handler.escalate_team("nonexistent")

    @pytest.mark.asyncio
    async def test_schedule_show_nonexistent_team(self, handler_setup):
        """Test showing schedule for non-existent team"""
        handler, db_session = handler_setup

        with pytest.raises(CommandError, match="Team not found"):
            await handler.schedule_show("nonexistent")

    @pytest.mark.asyncio
    async def test_shift_show_nonexistent_team(self, handler_setup):
        """Test showing shifts for non-existent team"""
        handler, db_session = handler_setup

        with pytest.raises(CommandError, match="Team not found"):
            await handler.shift_show("nonexistent")

    @pytest.mark.asyncio
    async def test_mention_duty_no_assignment(self, db_session: AsyncSession):
        """Test mentioning duty when no one is assigned"""
        workspace_id = 1

        team = Team(
            workspace_id=workspace_id,
            name="backend",
            display_name="Backend Team"
        )
        db_session.add(team)
        await db_session.commit()

        handler = CommandHandler(db_session, workspace_id)

        with pytest.raises(CommandError, match="No duty assigned"):
            await handler.mention_duty("backend")

    @pytest.mark.asyncio
    async def test_rotate_status_nonexistent_team(self, handler_setup):
        """Test rotation status for non-existent team"""
        handler, db_session = handler_setup

        with pytest.raises(CommandError, match="Team not found"):
            await handler.schedule_rotate_status("nonexistent")

    @pytest.mark.asyncio
    async def test_rotate_enable_with_users(self, db_session: AsyncSession):
        """Test enabling rotation with user order"""
        workspace_id = 1

        user1 = User(
            workspace_id=workspace_id,
            telegram_id=201,
            telegram_username="user1",
            first_name="User",
            last_name="One",
            display_name="User One"
        )
        user2 = User(
            workspace_id=workspace_id,
            telegram_id=202,
            telegram_username="user2",
            first_name="User",
            last_name="Two",
            display_name="User Two"
        )
        db_session.add(user1)
        db_session.add(user2)
        await db_session.commit()
        await db_session.refresh(user1)
        await db_session.refresh(user2)

        team = Team(
            workspace_id=workspace_id,
            name="backend",
            display_name="Backend Team"
        )
        db_session.add(team)
        await db_session.commit()

        handler = CommandHandler(db_session, workspace_id)
        result = await handler.schedule_rotate_enable("backend", [user1, user2])

        assert "enabled" in result.lower()

    @pytest.mark.asyncio
    async def test_incident_stop_no_active_incident(self, handler_setup):
        """Test stopping incident when none is active"""
        handler, db_session = handler_setup

        with pytest.raises(CommandError):
            await handler.incident_stop()

    @pytest.mark.asyncio
    async def test_incident_metrics_different_periods(self, db_session: AsyncSession):
        """Test incident metrics for different time periods"""
        workspace_id = 1
        handler = CommandHandler(db_session, workspace_id)

        # Test different period types
        result_week = await handler.incident_metrics("week")
        assert isinstance(result_week, str)

        result_month = await handler.incident_metrics("month")
        assert isinstance(result_month, str)

    @pytest.mark.asyncio
    async def test_empty_team_list(self, handler_setup):
        """Test listing teams when none exist"""
        handler, db_session = handler_setup

        result = await handler.team_list()
        assert result == "No teams configured."

    @pytest.mark.asyncio
    async def test_duty_today_empty_teams(self, handler_setup):
        """Test duty_today with no teams"""
        handler, db_session = handler_setup

        result = await handler.duty_today()
        assert result == "No teams configured."

    @pytest.mark.asyncio
    async def test_team_with_no_members(self, db_session: AsyncSession):
        """Test team info for team with no members"""
        workspace_id = 1

        team = Team(
            workspace_id=workspace_id,
            name="backend",
            display_name="Backend Team"
        )
        db_session.add(team)
        await db_session.commit()

        handler = CommandHandler(db_session, workspace_id)
        result = await handler.team_info("backend")

        assert "Backend Team" in result
        assert "No members" in result

    @pytest.mark.asyncio
    async def test_schedule_show_different_periods(self, db_session: AsyncSession):
        """Test schedule_show for different period types"""
        workspace_id = 1

        team = Team(
            workspace_id=workspace_id,
            name="backend",
            display_name="Backend Team"
        )
        db_session.add(team)
        await db_session.commit()

        handler = CommandHandler(db_session, workspace_id)

        # Test different period types
        result_week = await handler.schedule_show("backend", "week")
        assert isinstance(result_week, str)

        result_month = await handler.schedule_show("backend", "month")
        assert isinstance(result_month, str)

    @pytest.mark.asyncio
    async def test_shift_show_different_periods(self, db_session: AsyncSession):
        """Test shift_show for different period types"""
        workspace_id = 1

        team = Team(
            workspace_id=workspace_id,
            name="backend",
            display_name="Backend Team",
            has_shifts=True
        )
        db_session.add(team)
        await db_session.commit()

        handler = CommandHandler(db_session, workspace_id)

        # Test different period types
        result_week = await handler.shift_show("backend", "week")
        assert isinstance(result_week, str)

        result_month = await handler.shift_show("backend", "month")
        assert isinstance(result_month, str)


class TestTelegramHandlerEdgeCases:
    """Test TelegramHandler edge cases and error scenarios"""

    @pytest.mark.asyncio
    async def test_workspace_creation_without_title(self, db_session: AsyncSession):
        """Test workspace creation without chat title"""
        workspace_id = await get_or_create_telegram_workspace(db_session, 555, None)

        assert workspace_id is not None
        assert isinstance(workspace_id, int)

    @pytest.mark.asyncio
    async def test_workspace_creation_with_title(self, db_session: AsyncSession):
        """Test workspace creation with chat title"""
        workspace_id = await get_or_create_telegram_workspace(db_session, 556, "My Team Chat")

        assert workspace_id is not None
        assert isinstance(workspace_id, int)

    @pytest.mark.asyncio
    async def test_workspace_id_consistency(self, db_session: AsyncSession):
        """Test that workspace IDs are consistent"""
        workspace_id1 = await get_or_create_telegram_workspace(db_session, 557, "Chat 1")
        workspace_id2 = await get_or_create_telegram_workspace(db_session, 557, "Chat 1")

        assert workspace_id1 == workspace_id2

    @pytest.mark.asyncio
    async def test_help_command_format(self, db_session: AsyncSession):
        """Test help command returns properly formatted text"""
        workspace_id = 1
        handler = CommandHandler(db_session, workspace_id)

        result = await handler.help()

        # Check for key sections
        assert "Available Commands" in result
        assert "Duty" in result
        assert "Team Management" in result
        assert "Scheduling" in result
        assert "Shifts" in result
        assert "Escalation" in result
        assert "Incidents" in result
        assert "Date Format" in result

    @pytest.mark.asyncio
    async def test_team_list_with_team_lead(self, db_session: AsyncSession):
        """Test team list showing team leads"""
        workspace_id = 1

        lead = User(
            workspace_id=workspace_id,
            telegram_id=301,
            telegram_username="lead_user",
            first_name="Lead",
            last_name="User",
            display_name="Lead User"
        )
        db_session.add(lead)
        await db_session.commit()
        await db_session.refresh(lead)

        team = Team(
            workspace_id=workspace_id,
            name="backend",
            display_name="Backend Team",
            team_lead_id=lead.id
        )
        db_session.add(team)
        await db_session.commit()

        handler = CommandHandler(db_session, workspace_id)
        result = await handler.team_list()

        assert "Lead User" in result
        assert "backend" in result

    @pytest.mark.asyncio
    async def test_team_with_shifts_mode(self, db_session: AsyncSession):
        """Test team info for team with shifts enabled"""
        workspace_id = 1

        team = Team(
            workspace_id=workspace_id,
            name="backend",
            display_name="Backend Team",
            has_shifts=True
        )
        db_session.add(team)
        await db_session.commit()

        handler = CommandHandler(db_session, workspace_id)
        result = await handler.team_info("backend")

        assert "shifts" in result.lower()

    @pytest.mark.asyncio
    async def test_team_without_shifts_mode(self, db_session: AsyncSession):
        """Test team info for team without shifts"""
        workspace_id = 1

        team = Team(
            workspace_id=workspace_id,
            name="backend",
            display_name="Backend Team",
            has_shifts=False
        )
        db_session.add(team)
        await db_session.commit()

        handler = CommandHandler(db_session, workspace_id)
        result = await handler.team_info("backend")

        assert "duty" in result.lower()

    @pytest.mark.asyncio
    async def test_incident_start_and_list(self, db_session: AsyncSession):
        """Test creating and listing incidents"""
        workspace_id = 1
        handler = CommandHandler(db_session, workspace_id)

        # Start incident
        start_result = await handler.incident_start("Test Incident")
        assert isinstance(start_result, str)

        # List incidents
        list_result = await handler.incident_list()
        assert isinstance(list_result, str)
        assert "Test Incident" in list_result or "active" in list_result.lower()

    @pytest.mark.asyncio
    async def test_multiple_teams_duty_today(self, db_session: AsyncSession):
        """Test duty_today with multiple teams"""
        workspace_id = 1

        # Create users
        user1 = User(
            workspace_id=workspace_id,
            telegram_id=401,
            telegram_username="user1",
            first_name="User",
            last_name="One",
            display_name="User One"
        )
        user2 = User(
            workspace_id=workspace_id,
            telegram_id=402,
            telegram_username="user2",
            first_name="User",
            last_name="Two",
            display_name="User Two"
        )
        db_session.add(user1)
        db_session.add(user2)
        await db_session.commit()
        await db_session.refresh(user1)
        await db_session.refresh(user2)

        # Create teams
        team1 = Team(
            workspace_id=workspace_id,
            name="backend",
            display_name="Backend Team"
        )
        team2 = Team(
            workspace_id=workspace_id,
            name="frontend",
            display_name="Frontend Team"
        )
        db_session.add(team1)
        db_session.add(team2)
        await db_session.commit()
        await db_session.refresh(team1)
        await db_session.refresh(team2)

        # Create schedules
        today = date.today()
        schedule1 = Schedule(
            team_id=team1.id,
            user_id=user1.id,
            date=today,
            is_shift=False
        )
        schedule2 = Schedule(
            team_id=team2.id,
            user_id=user2.id,
            date=today,
            is_shift=False
        )
        db_session.add(schedule1)
        db_session.add(schedule2)
        await db_session.commit()

        handler = CommandHandler(db_session, workspace_id)
        result = await handler.duty_today(today=today)

        assert "Backend Team" in result
        assert "Frontend Team" in result
        assert "User One" in result
        assert "User Two" in result
