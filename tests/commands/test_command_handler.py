import pytest
from datetime import date, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from app.commands.handlers import CommandHandler
from app.commands.parser import CommandError
from app.models import Team, User, Schedule, Escalation, Incident, RotationConfig
from app.repositories import RotationConfigRepository


class TestCommandHandlerDuty:
    """Test duty-related commands"""

    @pytest.fixture
    async def setup_duty_team(self, db_session: AsyncSession):
        """Setup workspace, users and team for duty tests"""
        workspace_id = 1

        # Create users
        user1 = User(
            workspace_id=workspace_id,
            telegram_id=123,
            telegram_username="user1",
            first_name="John",
            last_name="Doe",
            display_name="John Doe"
        )
        user2 = User(
            workspace_id=workspace_id,
            telegram_id=124,
            telegram_username="user2",
            first_name="Jane",
            last_name="Smith",
            display_name="Jane Smith"
        )

        db_session.add(user1)
        db_session.add(user2)
        await db_session.flush()
        await db_session.refresh(user1)
        await db_session.refresh(user2)

        # Create team
        team = Team(
            workspace_id=workspace_id,
            name="backend",
            display_name="Backend Team"
        )
        db_session.add(team)
        await db_session.flush()
        await db_session.refresh(team)

        # Add members
        team.members.append(user1)
        team.members.append(user2)
        await db_session.flush()

        return workspace_id, team, user1, user2

    @pytest.mark.asyncio
    async def test_duty_today_no_teams(self, db_session: AsyncSession):
        """Test duty_today when no teams exist"""
        handler = CommandHandler(db_session, workspace_id=1)
        result = await handler.duty_today()
        assert result == "No teams configured."

    @pytest.mark.asyncio
    async def test_duty_today_with_team_no_schedule(self, db_session: AsyncSession, setup_duty_team):
        """Test duty_today with team but no schedule"""
        workspace_id, team, user1, user2 = setup_duty_team

        handler = CommandHandler(db_session, workspace_id=workspace_id)
        result = await handler.duty_today()

        assert "Backend Team" in result
        assert "не назначен" in result

    @pytest.mark.asyncio
    async def test_duty_today_with_schedule(self, db_session: AsyncSession, setup_duty_team):
        """Test duty_today with assigned duties"""
        workspace_id, team, user1, user2 = setup_duty_team
        today = date.today()

        # Create schedule entry
        schedule = Schedule(
            team_id=team.id,
            user_id=user1.id,
            date=today,
            is_shift=False
        )
        db_session.add(schedule)
        await db_session.flush()

        handler = CommandHandler(db_session, workspace_id=workspace_id)
        result = await handler.duty_today(today=today)

        assert "Backend Team" in result
        assert "John Doe" in result

    @pytest.mark.asyncio
    async def test_mention_duty_team_not_found(self, db_session: AsyncSession):
        """Test mention_duty with non-existent team"""
        handler = CommandHandler(db_session, workspace_id=1)

        with pytest.raises(CommandError, match="Team not found"):
            await handler.mention_duty("nonexistent")

    @pytest.mark.asyncio
    async def test_mention_duty_no_assignment(self, db_session: AsyncSession, setup_duty_team):
        """Test mention_duty when no one is assigned"""
        workspace_id, team, user1, user2 = setup_duty_team
        today = date.today()

        handler = CommandHandler(db_session, workspace_id=workspace_id)

        with pytest.raises(CommandError, match="No duty assigned"):
            await handler.mention_duty("backend", today=today)

    @pytest.mark.asyncio
    async def test_mention_duty_success(self, db_session: AsyncSession, setup_duty_team):
        """Test mention_duty with assigned duty"""
        workspace_id, team, user1, user2 = setup_duty_team
        today = date.today()

        # Create schedule entry
        schedule = Schedule(
            team_id=team.id,
            user_id=user1.id,
            date=today,
            is_shift=False
        )
        db_session.add(schedule)
        await db_session.flush()

        handler = CommandHandler(db_session, workspace_id=workspace_id)
        result = await handler.mention_duty("backend", today=today)

        assert "Backend Team" in result
        assert "user1" in result


class TestCommandHandlerTeam:
    """Test team management commands"""

    @pytest.fixture
    async def setup_team_data(self, db_session: AsyncSession):
        """Setup users and teams for team tests"""
        workspace_id = 1

        # Create users
        user1 = User(
            workspace_id=workspace_id,
            telegram_id=201,
            telegram_username="user_lead",
            first_name="Lead",
            last_name="User",
            display_name="Lead User"
        )
        user2 = User(
            workspace_id=workspace_id,
            telegram_id=202,
            telegram_username="user_member",
            first_name="Member",
            last_name="User",
            display_name="Member User"
        )

        db_session.add(user1)
        db_session.add(user2)
        await db_session.flush()
        await db_session.refresh(user1)
        await db_session.refresh(user2)

        return workspace_id, user1, user2

    @pytest.mark.asyncio
    async def test_team_list_empty(self, db_session: AsyncSession):
        """Test team_list when no teams exist"""
        handler = CommandHandler(db_session, workspace_id=1)
        result = await handler.team_list()
        assert result == "No teams configured."

    @pytest.mark.asyncio
    async def test_team_list_with_teams(self, db_session: AsyncSession, setup_team_data):
        """Test team_list with existing teams"""
        workspace_id, user1, user2 = setup_team_data

        team = Team(
            workspace_id=workspace_id,
            name="backend",
            display_name="Backend Team",
            team_lead_id=user1.id
        )
        db_session.add(team)
        await db_session.flush()

        handler = CommandHandler(db_session, workspace_id=workspace_id)
        result = await handler.team_list()

        assert "Backend Team" in result
        assert "backend" in result
        assert "Lead User" in result

    @pytest.mark.asyncio
    async def test_team_info_not_found(self, db_session: AsyncSession):
        """Test team_info with non-existent team"""
        handler = CommandHandler(db_session, workspace_id=1)

        with pytest.raises(CommandError, match="Team not found"):
            await handler.team_info("nonexistent")

    @pytest.mark.asyncio
    async def test_team_info_success(self, db_session: AsyncSession, setup_team_data):
        """Test team_info with existing team"""
        workspace_id, user1, user2 = setup_team_data

        team = Team(
            workspace_id=workspace_id,
            name="backend",
            display_name="Backend Team",
            team_lead_id=user1.id
        )
        db_session.add(team)
        await db_session.flush()

        team.members.append(user1)
        team.members.append(user2)
        await db_session.flush()
        await db_session.refresh(team, ["members", "team_lead_user"])

        handler = CommandHandler(db_session, workspace_id=workspace_id)
        try:
            result = await handler.team_info("backend")
        except Exception:
            import traceback
            traceback.print_exc()
            raise

        assert "Backend Team" in result
        assert "Lead User" in result
        assert "Member User" in result

    @pytest.mark.asyncio
    async def test_team_add_success(self, db_session: AsyncSession):
        """Test team_add creates a new team"""
        workspace_id = 1

        handler = CommandHandler(db_session, workspace_id=workspace_id)
        result = await handler.team_add("backend", "Backend Team")

        assert "Backend Team" in result
        assert "created" in result

    @pytest.mark.asyncio
    async def test_team_add_duplicate(self, db_session: AsyncSession):
        """Test team_add with duplicate name"""
        workspace_id = 1

        # Create first team
        team = Team(
            workspace_id=workspace_id,
            name="backend",
            display_name="Backend Team"
        )
        db_session.add(team)
        await db_session.flush()

        handler = CommandHandler(db_session, workspace_id=workspace_id)

        with pytest.raises(CommandError, match="Team already exists"):
            await handler.team_add("backend", "Another Backend")

    @pytest.mark.asyncio
    async def test_team_edit_name(self, db_session: AsyncSession):
        """Test team_edit_name renames team"""
        workspace_id = 1

        team = Team(
            workspace_id=workspace_id,
            name="backend",
            display_name="Backend Team"
        )
        db_session.add(team)
        await db_session.flush()

        handler = CommandHandler(db_session, workspace_id=workspace_id)
        result = await handler.team_edit_name("backend", "api")

        assert "api" in result
        assert "renamed" in result

    @pytest.mark.asyncio
    async def test_team_edit_display(self, db_session: AsyncSession):
        """Test team_edit_display changes display name"""
        workspace_id = 1

        team = Team(
            workspace_id=workspace_id,
            name="backend",
            display_name="Backend Team"
        )
        db_session.add(team)
        await db_session.flush()

        handler = CommandHandler(db_session, workspace_id=workspace_id)
        result = await handler.team_edit_display("backend", "Backend Platform")

        assert "Backend Platform" in result

    @pytest.mark.asyncio
    async def test_team_edit_shifts_enable(self, db_session: AsyncSession):
        """Test enabling shifts for team"""
        workspace_id = 1

        team = Team(
            workspace_id=workspace_id,
            name="backend",
            display_name="Backend Team",
            has_shifts=False
        )
        db_session.add(team)
        await db_session.flush()

        handler = CommandHandler(db_session, workspace_id=workspace_id)
        result = await handler.team_edit_shifts("backend", True)

        assert "enabled" in result

    @pytest.mark.asyncio
    async def test_team_set_lead(self, db_session: AsyncSession, setup_team_data):
        """Test team_set_lead assigns team lead"""
        workspace_id, user1, user2 = setup_team_data

        team = Team(
            workspace_id=workspace_id,
            name="backend",
            display_name="Backend Team"
        )
        db_session.add(team)
        await db_session.flush()

        handler = CommandHandler(db_session, workspace_id=workspace_id)
        result = await handler.team_set_lead("backend", user1)

        assert user1.display_name in result

    @pytest.mark.asyncio
    async def test_team_add_member(self, db_session: AsyncSession, setup_team_data):
        """Test team_add_member adds member to team"""
        workspace_id, user1, user2 = setup_team_data

        team = Team(
            workspace_id=workspace_id,
            name="backend",
            display_name="Backend Team"
        )
        db_session.add(team)
        await db_session.flush()

        handler = CommandHandler(db_session, workspace_id=workspace_id)
        result = await handler.team_add_member("backend", user1)

        assert user1.display_name in result
        assert "added" in result

    @pytest.mark.asyncio
    async def test_team_remove_member(self, db_session: AsyncSession, setup_team_data):
        """Test team_remove_member removes member from team"""
        workspace_id, user1, user2 = setup_team_data

        team = Team(
            workspace_id=workspace_id,
            name="backend",
            display_name="Backend Team"
        )
        db_session.add(team)
        await db_session.flush()

        team.members.append(user1)
        await db_session.flush()

        handler = CommandHandler(db_session, workspace_id=workspace_id)
        result = await handler.team_remove_member("backend", user1)

        assert user1.display_name in result
        assert "removed" in result

    @pytest.mark.asyncio
    async def test_team_remove_member_not_in_team(self, db_session: AsyncSession, setup_team_data):
        """Test team_remove_member with non-member"""
        workspace_id, user1, user2 = setup_team_data

        team = Team(
            workspace_id=workspace_id,
            name="backend",
            display_name="Backend Team"
        )
        db_session.add(team)
        await db_session.flush()

        handler = CommandHandler(db_session, workspace_id=workspace_id)

        with pytest.raises(CommandError, match="is not in"):
            await handler.team_remove_member("backend", user1)

    @pytest.mark.asyncio
    async def test_team_move_member(self, db_session: AsyncSession, setup_team_data):
        """Test team_move_member moves member between teams"""
        workspace_id, user1, user2 = setup_team_data

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
        await db_session.flush()

        team1.members.append(user1)
        await db_session.flush()

        handler = CommandHandler(db_session, workspace_id=workspace_id)
        result = await handler.team_move_member(user1, "backend", "frontend")

        assert user1.display_name in result

    @pytest.mark.asyncio
    async def test_team_delete(self, db_session: AsyncSession):
        """Test team_delete removes team"""
        workspace_id = 1

        team = Team(
            workspace_id=workspace_id,
            name="backend",
            display_name="Backend Team"
        )
        db_session.add(team)
        await db_session.flush()

        handler = CommandHandler(db_session, workspace_id=workspace_id)
        result = await handler.team_delete("backend")

        assert "deleted" in result


class TestCommandHandlerSchedule:
    """Test schedule commands"""

    @pytest.fixture
    async def setup_schedule_data(self, db_session: AsyncSession):
        """Setup data for schedule tests"""
        workspace_id = 1

        user = User(
            workspace_id=workspace_id,
            telegram_id=301,
            telegram_username="user",
            first_name="Test",
            last_name="User",
            display_name="Test User"
        )

        db_session.add(user)
        await db_session.flush()
        await db_session.refresh(user)

        team = Team(
            workspace_id=workspace_id,
            name="backend",
            display_name="Backend Team"
        )
        db_session.add(team)
        await db_session.flush()
        await db_session.refresh(team)

        team.members.append(user)
        await db_session.flush()

        return workspace_id, team, user

    @pytest.mark.asyncio
    async def test_schedule_show_team_not_found(self, db_session: AsyncSession):
        """Test schedule_show with non-existent team"""
        handler = CommandHandler(db_session, workspace_id=1)

        with pytest.raises(CommandError, match="Team not found"):
            await handler.schedule_show("nonexistent")

    @pytest.mark.asyncio
    async def test_schedule_show_week(self, db_session: AsyncSession, setup_schedule_data):
        """Test schedule_show displays weekly schedule"""
        workspace_id, team, user = setup_schedule_data
        today = date.today()

        handler = CommandHandler(db_session, workspace_id=workspace_id)
        result = await handler.schedule_show("backend", "week", today=today)

        assert isinstance(result, str)
        assert len(result) > 0

    @pytest.mark.asyncio
    async def test_schedule_set(self, db_session: AsyncSession, setup_schedule_data):
        """Test schedule_set assigns duty"""
        workspace_id, team, user = setup_schedule_data
        today = date.today()

        handler = CommandHandler(db_session, workspace_id=workspace_id)
        result = await handler.schedule_set("backend", today, user, today=today)

        assert "set" in result.lower()

    @pytest.mark.asyncio
    async def test_schedule_clear(self, db_session: AsyncSession, setup_schedule_data):
        """Test schedule_clear removes duty"""
        workspace_id, team, user = setup_schedule_data
        today = date.today()

        # Set duty first
        schedule = Schedule(
            team_id=team.id,
            user_id=user.id,
            date=today,
            is_shift=False
        )
        db_session.add(schedule)
        await db_session.flush()

        handler = CommandHandler(db_session, workspace_id=workspace_id)
        result = await handler.schedule_clear("backend", today, today=today)

        assert "cleared" in result.lower()


class TestCommandHandlerShift:
    """Test shift commands"""

    @pytest.fixture
    async def setup_shift_data(self, db_session: AsyncSession):
        """Setup data for shift tests"""
        workspace_id = 1

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
        await db_session.flush()
        await db_session.refresh(user1)
        await db_session.refresh(user2)

        team = Team(
            workspace_id=workspace_id,
            name="backend",
            display_name="Backend Team",
            has_shifts=True
        )
        db_session.add(team)
        await db_session.flush()
        await db_session.refresh(team)

        team.members.append(user1)
        team.members.append(user2)
        await db_session.flush()

        return workspace_id, team, user1, user2

    @pytest.mark.asyncio
    async def test_shift_show_team_not_found(self, db_session: AsyncSession):
        """Test shift_show with non-existent team"""
        handler = CommandHandler(db_session, workspace_id=1)

        with pytest.raises(CommandError, match="Team not found"):
            await handler.shift_show("nonexistent")

    @pytest.mark.asyncio
    async def test_shift_show_week(self, db_session: AsyncSession, setup_shift_data):
        """Test shift_show displays weekly shifts"""
        workspace_id, team, user1, user2 = setup_shift_data
        today = date.today()

        handler = CommandHandler(db_session, workspace_id=workspace_id)
        result = await handler.shift_show("backend", "week", today=today)

        assert isinstance(result, str)
        assert len(result) > 0

    @pytest.mark.asyncio
    async def test_shift_set(self, db_session: AsyncSession, setup_shift_data):
        """Test shift_set assigns shift"""
        workspace_id, team, user1, user2 = setup_shift_data
        today = date.today()

        handler = CommandHandler(db_session, workspace_id=workspace_id)
        result = await handler.shift_set("backend", today, [user1, user2], today=today)

        assert isinstance(result, str)

    @pytest.mark.asyncio
    async def test_shift_add_user(self, db_session: AsyncSession, setup_shift_data):
        """Test shift_add_user adds member to shift"""
        workspace_id, team, user1, user2 = setup_shift_data
        today = date.today()

        handler = CommandHandler(db_session, workspace_id=workspace_id)
        result = await handler.shift_add_user("backend", today, user1, today=today)

        assert "added" in result.lower()

    @pytest.mark.asyncio
    async def test_shift_remove_user(self, db_session: AsyncSession, setup_shift_data):
        """Test shift_remove_user removes member from shift"""
        workspace_id, team, user1, user2 = setup_shift_data
        today = date.today()

        # Set shift first
        schedule = Schedule(
            team_id=team.id,
            user_id=user1.id,
            date=today,
            is_shift=True
        )
        db_session.add(schedule)
        await db_session.flush()

        handler = CommandHandler(db_session, workspace_id=workspace_id)
        result = await handler.shift_remove_user("backend", today, user1, today=today)

        assert "removed" in result.lower()

    @pytest.mark.asyncio
    async def test_shift_clear(self, db_session: AsyncSession, setup_shift_data):
        """Test shift_clear removes all members from shift"""
        workspace_id, team, user1, user2 = setup_shift_data
        today = date.today()

        handler = CommandHandler(db_session, workspace_id=workspace_id)
        result = await handler.shift_clear("backend", today, today=today)

        assert "cleared" in result.lower()


class TestCommandHandlerEscalation:
    """Test escalation commands"""

    @pytest.fixture
    async def setup_escalation_data(self, db_session: AsyncSession):
        """Setup data for escalation tests"""
        workspace_id = 1

        user1 = User(
            workspace_id=workspace_id,
            telegram_id=501,
            telegram_username="lead",
            first_name="Team",
            last_name="Lead",
            display_name="Team Lead"
        )
        user2 = User(
            workspace_id=workspace_id,
            telegram_id=502,
            telegram_username="cto",
            first_name="CTO",
            last_name="User",
            display_name="CTO User"
        )

        db_session.add(user1)
        db_session.add(user2)
        await db_session.flush()
        await db_session.refresh(user1)
        await db_session.refresh(user2)

        team = Team(
            workspace_id=workspace_id,
            name="backend",
            display_name="Backend Team",
            team_lead_id=user1.id
        )
        db_session.add(team)
        await db_session.flush()
        await db_session.refresh(team)

        return workspace_id, team, user1, user2

    @pytest.mark.asyncio
    async def test_escalation_show(self, db_session: AsyncSession, setup_escalation_data):
        """Test escalation_show displays settings"""
        workspace_id, team, user1, user2 = setup_escalation_data

        handler = CommandHandler(db_session, workspace_id=workspace_id)
        result = await handler.escalation_show()

        assert isinstance(result, str)

    @pytest.mark.asyncio
    async def test_escalation_set_cto(self, db_session: AsyncSession, setup_escalation_data):
        """Test escalation_set_cto sets CTO"""
        workspace_id, team, user1, user2 = setup_escalation_data

        handler = CommandHandler(db_session, workspace_id=workspace_id)
        result = await handler.escalation_set_cto(user2)

        assert user2.display_name in result

    @pytest.mark.asyncio
    async def test_escalate_team(self, db_session: AsyncSession, setup_escalation_data):
        """Test escalate_team escalates to team lead"""
        workspace_id, team, user1, user2 = setup_escalation_data

        handler = CommandHandler(db_session, workspace_id=workspace_id)
        result = await handler.escalate_team("backend")

        assert isinstance(result, str)

    @pytest.mark.asyncio
    async def test_escalate_cto(self, db_session: AsyncSession, setup_escalation_data):
        """Test escalate_cto escalates to CTO"""
        workspace_id, team, user1, user2 = setup_escalation_data

        # Set CTO first
        escalation = Escalation(
            team_id=None,
            cto_id=user2.id
        )
        db_session.add(escalation)
        await db_session.flush()

        handler = CommandHandler(db_session, workspace_id=workspace_id)
        result = await handler.escalate_cto()

        assert isinstance(result, str)


class TestCommandHandlerRotation:
    """Test rotation commands"""

    @pytest.fixture
    async def setup_rotation_data(self, db_session: AsyncSession):
        """Setup data for rotation tests"""
        workspace_id = 1

        user1 = User(
            workspace_id=workspace_id,
            telegram_id=601,
            telegram_username="user1",
            first_name="User",
            last_name="One",
            display_name="User One"
        )
        user2 = User(
            workspace_id=workspace_id,
            telegram_id=602,
            telegram_username="user2",
            first_name="User",
            last_name="Two",
            display_name="User Two"
        )

        db_session.add(user1)
        db_session.add(user2)
        await db_session.flush()
        await db_session.refresh(user1)
        await db_session.refresh(user2)

        team = Team(
            workspace_id=workspace_id,
            name="backend",
            display_name="Backend Team"
        )
        db_session.add(team)
        await db_session.flush()
        await db_session.refresh(team)

        team.members.append(user1)
        team.members.append(user2)
        await db_session.flush()

        return workspace_id, team, user1, user2

    @pytest.mark.asyncio
    async def test_schedule_rotate_status(self, db_session: AsyncSession, setup_rotation_data):
        """Test schedule_rotate_status shows rotation status"""
        workspace_id, team, user1, user2 = setup_rotation_data

        handler = CommandHandler(db_session, workspace_id=workspace_id)
        result = await handler.schedule_rotate_status("backend")

        assert isinstance(result, str)

    @pytest.mark.asyncio
    async def test_schedule_rotate_enable(self, db_session: AsyncSession, setup_rotation_data):
        """Test schedule_rotate_enable enables rotation"""
        workspace_id, team, user1, user2 = setup_rotation_data

        handler = CommandHandler(db_session, workspace_id=workspace_id)
        result = await handler.schedule_rotate_enable("backend", [user1, user2])

        assert "enabled" in result.lower()

    @pytest.mark.asyncio
    async def test_schedule_rotate_assign(self, db_session: AsyncSession, setup_rotation_data):
        """Test schedule_rotate_assign assigns next person"""
        workspace_id, team, user1, user2 = setup_rotation_data

        # Enable rotation first
        rotation = RotationConfig(
            team_id=team.id,
            member_ids=[user1.id, user2.id],
            enabled=True
        )
        db_session.add(rotation)
        await db_session.flush()

        handler = CommandHandler(db_session, workspace_id=workspace_id)
        result = await handler.schedule_rotate_assign("backend", date.today().strftime("%d.%m.%Y"))

        assert isinstance(result, str)

    @pytest.mark.asyncio
    async def test_schedule_rotate_disable(self, db_session: AsyncSession, setup_rotation_data):
        """Test schedule_rotate_disable disables rotation"""
        workspace_id, team, user1, user2 = setup_rotation_data

        # Enable rotation first
        rotation = RotationConfig(
            team_id=team.id,
            member_ids=[user1.id, user2.id],
            enabled=True
        )
        db_session.add(rotation)
        await db_session.flush()

        handler = CommandHandler(db_session, workspace_id=workspace_id)
        result = await handler.schedule_rotate_disable("backend")

        assert "disabled" in result.lower()


class TestCommandHandlerIncident:
    """Test incident commands"""

    @pytest.fixture
    async def setup_incident_data(self, db_session: AsyncSession):
        """Setup data for incident tests"""
        workspace_id = 1
        return workspace_id

    @pytest.mark.asyncio
    async def test_incident_list_empty(self, db_session: AsyncSession, setup_incident_data):
        """Test incident_list with no incidents"""
        workspace_id = setup_incident_data

        handler = CommandHandler(db_session, workspace_id=workspace_id)
        result = await handler.incident_list()

        assert isinstance(result, str)

    @pytest.mark.asyncio
    async def test_incident_start(self, db_session: AsyncSession, setup_incident_data):
        """Test incident_start creates incident"""
        workspace_id = setup_incident_data

        handler = CommandHandler(db_session, workspace_id=workspace_id)
        result = await handler.incident_start("Test Incident")

        assert isinstance(result, str)

    @pytest.mark.asyncio
    async def test_incident_stop_no_active(self, db_session: AsyncSession, setup_incident_data):
        """Test incident_stop when no active incident"""
        workspace_id = setup_incident_data

        handler = CommandHandler(db_session, workspace_id=workspace_id)

        with pytest.raises(CommandError):
            await handler.incident_stop()

    @pytest.mark.asyncio
    async def test_incident_stop_active(self, db_session: AsyncSession, setup_incident_data):
        """Test incident_stop closes active incident"""
        workspace_id = setup_incident_data

        from datetime import datetime
        incident = Incident(
            workspace_id=workspace_id,
            name="Test Incident",
            status="active",
            start_time=datetime.utcnow()
        )
        db_session.add(incident)
        await db_session.flush()

        handler = CommandHandler(db_session, workspace_id=workspace_id)
        result = await handler.incident_stop()

        assert isinstance(result, str)

    @pytest.mark.asyncio
    async def test_incident_metrics(self, db_session: AsyncSession, setup_incident_data):
        """Test incident_metrics returns metrics"""
        workspace_id = setup_incident_data

        handler = CommandHandler(db_session, workspace_id=workspace_id)
        result = await handler.incident_metrics("week")

        assert isinstance(result, str)


class TestCommandHandlerHelp:
    """Test help command"""

    @pytest.mark.asyncio
    async def test_help_command(self, db_session: AsyncSession):
        """Test help command returns help text"""
        handler = CommandHandler(db_session, workspace_id=1)
        result = await handler.help()

        assert isinstance(result, str)
        assert "Available Commands" in result
        assert "Duty" in result
        assert "Team Management" in result
        assert "Scheduling" in result
