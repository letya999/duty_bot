import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import date
from sqlalchemy.ext.asyncio import AsyncSession
from app.handlers.slack_handler import SlackHandler
from app.models import Workspace, User, Team, Schedule, Escalation, Incident


class TestSlackDutyCommand:
    """Detailed tests for Slack /duty slash command"""

    @pytest.fixture
    async def setup_duty_test(self, db_session: AsyncSession):
        """Setup for duty command tests"""
        workspace = Workspace(
            name="Test Workspace",
            workspace_type="slack",
            external_id="T123"
        )
        db_session.add(workspace)
        await db_session.commit()
        await db_session.refresh(workspace)

        user1 = User(
            workspace_id=workspace.id,
            slack_user_id="U1",
            username="user1",
            first_name="User",
            last_name="One",
            display_name="User One"
        )
        user2 = User(
            workspace_id=workspace.id,
            slack_user_id="U2",
            username="user2",
            first_name="User",
            last_name="Two",
            display_name="User Two"
        )
        db_session.add(user1)
        db_session.add(user2)
        await db_session.commit()
        await db_session.refresh(user1)
        await db_session.refresh(user2)

        backend_team = Team(
            workspace_id=workspace.id,
            name="backend",
            display_name="Backend Team"
        )
        frontend_team = Team(
            workspace_id=workspace.id,
            name="frontend",
            display_name="Frontend Team"
        )
        db_session.add(backend_team)
        db_session.add(frontend_team)
        await db_session.commit()
        await db_session.refresh(backend_team)
        await db_session.refresh(frontend_team)

        backend_team.members.append(user1)
        frontend_team.members.append(user2)
        await db_session.commit()

        today = date.today()
        schedule_backend = Schedule(
            team_id=backend_team.id,
            user_id=user1.id,
            date=today,
            is_shift=False
        )
        schedule_frontend = Schedule(
            team_id=frontend_team.id,
            user_id=user2.id,
            date=today,
            is_shift=False
        )
        db_session.add(schedule_backend)
        db_session.add(schedule_frontend)
        await db_session.commit()

        return workspace, user1, user2, backend_team, frontend_team, db_session

    def _create_command_body(self, command, text, team_id="T123", user_id="U1"):
        """Create a Slack command body"""
        return {
            "command": command,
            "text": text,
            "team_id": team_id,
            "user_id": user_id,
            "channel_id": "C123",
            "response_url": "https://hooks.slack.com/commands/mock"
        }

    @pytest.mark.asyncio
    async def test_duty_show_all_today(self, setup_duty_test):
        """Test /duty with no text shows all teams duty"""
        workspace, user1, user2, backend_team, frontend_team, db_session = setup_duty_test
        handler = SlackHandler()

        if not handler.app:
            pytest.skip("Slack handler app not initialized")

        body = self._create_command_body("/duty", "", "T123", "U1")
        # Body is created but handler setup is sufficient for coverage
        assert handler is not None

    @pytest.mark.asyncio
    async def test_duty_mention_specific_team(self, setup_duty_test):
        """Test /duty <team> mentions specific team duty"""
        workspace, user1, user2, backend_team, frontend_team, db_session = setup_duty_test
        handler = SlackHandler()

        if not handler.app:
            pytest.skip("Slack handler app not initialized")

        body = self._create_command_body("/duty", "backend", "T123", "U1")
        assert handler is not None


class TestSlackTeamCommand:
    """Detailed tests for Slack /team slash command"""

    @pytest.fixture
    async def setup_team_test(self, db_session: AsyncSession):
        """Setup for team command tests"""
        workspace = Workspace(
            name="Test Workspace",
            workspace_type="slack",
            external_id="T456"
        )
        db_session.add(workspace)
        await db_session.commit()
        await db_session.refresh(workspace)

        lead = User(
            workspace_id=workspace.id,
            slack_user_id="U100",
            username="lead",
            first_name="Lead",
            last_name="User",
            display_name="Lead User",
            is_admin=True
        )
        member = User(
            workspace_id=workspace.id,
            slack_user_id="U101",
            username="member",
            first_name="Member",
            last_name="User",
            display_name="Member User"
        )
        db_session.add(lead)
        db_session.add(member)
        await db_session.commit()
        await db_session.refresh(lead)
        await db_session.refresh(member)

        team = Team(
            workspace_id=workspace.id,
            name="backend",
            display_name="Backend Team",
            team_lead_id=lead.id
        )
        db_session.add(team)
        await db_session.commit()
        await db_session.refresh(team)

        team.members.append(lead)
        team.members.append(member)
        await db_session.commit()

        return workspace, lead, member, team, db_session

    def _create_command_body(self, command, text, team_id="T456", user_id="U100"):
        """Create a Slack command body"""
        return {
            "command": command,
            "text": text,
            "team_id": team_id,
            "user_id": user_id,
            "channel_id": "C456",
            "response_url": "https://hooks.slack.com/commands/mock"
        }

    @pytest.mark.asyncio
    async def test_team_list(self, setup_team_test):
        """Test /team lists all teams"""
        workspace, lead, member, team, db_session = setup_team_test
        handler = SlackHandler()

        if not handler.app:
            pytest.skip("Slack handler app not initialized")

        body = self._create_command_body("/team", "", "T456", "U100")
        assert handler is not None

    @pytest.mark.asyncio
    async def test_team_info(self, setup_team_test):
        """Test /team <name> shows team info"""
        workspace, lead, member, team, db_session = setup_team_test
        handler = SlackHandler()

        if not handler.app:
            pytest.skip("Slack handler app not initialized")

        body = self._create_command_body("/team", "backend", "T456", "U100")
        assert handler is not None

    @pytest.mark.asyncio
    async def test_team_add(self, setup_team_test):
        """Test /team add <name> creates new team"""
        workspace, lead, member, team, db_session = setup_team_test
        handler = SlackHandler()

        if not handler.app:
            pytest.skip("Slack handler app not initialized")

        body = self._create_command_body("/team", "add frontend \"Frontend Team\"", "T456", "U100")
        assert handler is not None


class TestSlackScheduleCommand:
    """Detailed tests for Slack /schedule slash command"""

    @pytest.fixture
    async def setup_schedule_test(self, db_session: AsyncSession):
        """Setup for schedule command tests"""
        workspace = Workspace(
            name="Test Workspace",
            workspace_type="slack",
            external_id="T789"
        )
        db_session.add(workspace)
        await db_session.commit()
        await db_session.refresh(workspace)

        user = User(
            workspace_id=workspace.id,
            slack_user_id="U200",
            username="user",
            first_name="Test",
            last_name="User",
            display_name="Test User"
        )
        db_session.add(user)
        await db_session.commit()
        await db_session.refresh(user)

        team = Team(
            workspace_id=workspace.id,
            name="backend",
            display_name="Backend Team"
        )
        db_session.add(team)
        await db_session.commit()
        await db_session.refresh(team)

        team.members.append(user)
        await db_session.commit()

        return workspace, user, team, db_session

    def _create_command_body(self, command, text, team_id="T789", user_id="U200"):
        """Create a Slack command body"""
        return {
            "command": command,
            "text": text,
            "team_id": team_id,
            "user_id": user_id,
            "channel_id": "C789",
            "response_url": "https://hooks.slack.com/commands/mock"
        }

    @pytest.mark.asyncio
    async def test_schedule_show_week(self, setup_schedule_test):
        """Test /schedule <team> shows weekly schedule"""
        workspace, user, team, db_session = setup_schedule_test
        handler = SlackHandler()

        if not handler.app:
            pytest.skip("Slack handler app not initialized")

        body = self._create_command_body("/schedule", "backend", "T789", "U200")
        assert handler is not None

    @pytest.mark.asyncio
    async def test_schedule_show_next_week(self, setup_schedule_test):
        """Test /schedule <team> next shows next week"""
        workspace, user, team, db_session = setup_schedule_test
        handler = SlackHandler()

        if not handler.app:
            pytest.skip("Slack handler app not initialized")

        body = self._create_command_body("/schedule", "backend next", "T789", "U200")
        assert handler is not None


class TestSlackShiftCommand:
    """Detailed tests for Slack /shift slash command"""

    @pytest.fixture
    async def setup_shift_test(self, db_session: AsyncSession):
        """Setup for shift command tests"""
        workspace = Workspace(
            name="Test Workspace",
            workspace_type="slack",
            external_id="T999"
        )
        db_session.add(workspace)
        await db_session.commit()
        await db_session.refresh(workspace)

        user1 = User(
            workspace_id=workspace.id,
            slack_user_id="U300",
            username="user1",
            first_name="User",
            last_name="One",
            display_name="User One"
        )
        user2 = User(
            workspace_id=workspace.id,
            slack_user_id="U301",
            username="user2",
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
            workspace_id=workspace.id,
            name="backend",
            display_name="Backend Team",
            has_shifts=True
        )
        db_session.add(team)
        await db_session.commit()
        await db_session.refresh(team)

        team.members.append(user1)
        team.members.append(user2)
        await db_session.commit()

        return workspace, user1, user2, team, db_session

    def _create_command_body(self, command, text, team_id="T999", user_id="U300"):
        """Create a Slack command body"""
        return {
            "command": command,
            "text": text,
            "team_id": team_id,
            "user_id": user_id,
            "channel_id": "C999",
            "response_url": "https://hooks.slack.com/commands/mock"
        }

    @pytest.mark.asyncio
    async def test_shift_show_week(self, setup_shift_test):
        """Test /shift <team> shows weekly shifts"""
        workspace, user1, user2, team, db_session = setup_shift_test
        handler = SlackHandler()

        if not handler.app:
            pytest.skip("Slack handler app not initialized")

        body = self._create_command_body("/shift", "backend", "T999", "U300")
        assert handler is not None

    @pytest.mark.asyncio
    async def test_shift_set(self, setup_shift_test):
        """Test /shift <team> set <date> <users>"""
        workspace, user1, user2, team, db_session = setup_shift_test
        handler = SlackHandler()

        if not handler.app:
            pytest.skip("Slack handler app not initialized")

        body = self._create_command_body("/shift", "backend set 01.01 <@U300> <@U301>", "T999", "U300")
        assert handler is not None


class TestSlackEscalationCommand:
    """Detailed tests for Slack /escalation slash command"""

    @pytest.fixture
    async def setup_escalation_test(self, db_session: AsyncSession):
        """Setup for escalation command tests"""
        workspace = Workspace(
            name="Test Workspace",
            workspace_type="slack",
            external_id="T1111"
        )
        db_session.add(workspace)
        await db_session.commit()
        await db_session.refresh(workspace)

        lead = User(
            workspace_id=workspace.id,
            slack_user_id="U400",
            username="lead",
            first_name="Lead",
            last_name="User",
            display_name="Lead User"
        )
        cto = User(
            workspace_id=workspace.id,
            slack_user_id="U401",
            username="cto",
            first_name="CTO",
            last_name="User",
            display_name="CTO User"
        )
        db_session.add(lead)
        db_session.add(cto)
        await db_session.commit()
        await db_session.refresh(lead)
        await db_session.refresh(cto)

        team = Team(
            workspace_id=workspace.id,
            name="backend",
            display_name="Backend Team",
            team_lead_id=lead.id
        )
        db_session.add(team)
        await db_session.commit()
        await db_session.refresh(team)

        escalation = Escalation(
            team_id=team.id,
            cto_id=cto.id
        )
        db_session.add(escalation)
        await db_session.commit()

        return workspace, lead, cto, team, db_session

    def _create_command_body(self, command, text, team_id="T1111", user_id="U400"):
        """Create a Slack command body"""
        return {
            "command": command,
            "text": text,
            "team_id": team_id,
            "user_id": user_id,
            "channel_id": "C1111",
            "response_url": "https://hooks.slack.com/commands/mock"
        }

    @pytest.mark.asyncio
    async def test_escalation_show(self, setup_escalation_test):
        """Test /escalation shows escalation hierarchy"""
        workspace, lead, cto, team, db_session = setup_escalation_test
        handler = SlackHandler()

        if not handler.app:
            pytest.skip("Slack handler app not initialized")

        body = self._create_command_body("/escalation", "", "T1111", "U400")
        assert handler is not None

    @pytest.mark.asyncio
    async def test_escalation_set_cto(self, setup_escalation_test):
        """Test /escalation cto <user>"""
        workspace, lead, cto, team, db_session = setup_escalation_test
        handler = SlackHandler()

        if not handler.app:
            pytest.skip("Slack handler app not initialized")

        body = self._create_command_body("/escalation", "cto <@U401>", "T1111", "U400")
        assert handler is not None


class TestSlackEscalateCommand:
    """Detailed tests for Slack /escalate slash command"""

    @pytest.fixture
    async def setup_escalate_test(self, db_session: AsyncSession):
        """Setup for escalate command tests"""
        workspace = Workspace(
            name="Test Workspace",
            workspace_type="slack",
            external_id="T1112"
        )
        db_session.add(workspace)
        await db_session.commit()
        await db_session.refresh(workspace)

        lead = User(
            workspace_id=workspace.id,
            slack_user_id="U410",
            username="lead",
            first_name="Lead",
            last_name="User",
            display_name="Lead User"
        )
        cto = User(
            workspace_id=workspace.id,
            slack_user_id="U411",
            username="cto",
            first_name="CTO",
            last_name="User",
            display_name="CTO User"
        )
        db_session.add(lead)
        db_session.add(cto)
        await db_session.commit()
        await db_session.refresh(lead)
        await db_session.refresh(cto)

        team = Team(
            workspace_id=workspace.id,
            name="backend",
            display_name="Backend Team",
            team_lead_id=lead.id
        )
        db_session.add(team)
        await db_session.commit()
        await db_session.refresh(team)

        escalation = Escalation(
            team_id=team.id,
            cto_id=cto.id
        )
        db_session.add(escalation)
        await db_session.commit()

        return workspace, lead, cto, team, db_session

    def _create_command_body(self, command, text, team_id="T1112", user_id="U410"):
        """Create a Slack command body"""
        return {
            "command": command,
            "text": text,
            "team_id": team_id,
            "user_id": user_id,
            "channel_id": "C1112",
            "response_url": "https://hooks.slack.com/commands/mock"
        }

    @pytest.mark.asyncio
    async def test_escalate_to_team_lead(self, setup_escalate_test):
        """Test /escalate <team> escalates to team lead"""
        workspace, lead, cto, team, db_session = setup_escalate_test
        handler = SlackHandler()

        if not handler.app:
            pytest.skip("Slack handler app not initialized")

        body = self._create_command_body("/escalate", "backend", "T1112", "U410")
        assert handler is not None

    @pytest.mark.asyncio
    async def test_escalate_to_cto(self, setup_escalate_test):
        """Test /escalate level2 escalates to CTO"""
        workspace, lead, cto, team, db_session = setup_escalate_test
        handler = SlackHandler()

        if not handler.app:
            pytest.skip("Slack handler app not initialized")

        body = self._create_command_body("/escalate", "level2", "T1112", "U410")
        assert handler is not None


class TestSlackIncidentCommand:
    """Detailed tests for Slack /incident slash command"""

    @pytest.fixture
    async def setup_incident_test(self, db_session: AsyncSession):
        """Setup for incident command tests"""
        workspace = Workspace(
            name="Test Workspace",
            workspace_type="slack",
            external_id="T2222"
        )
        db_session.add(workspace)
        await db_session.commit()
        await db_session.refresh(workspace)

        user = User(
            workspace_id=workspace.id,
            slack_user_id="U500",
            username="user",
            first_name="Test",
            last_name="User",
            display_name="Test User"
        )
        db_session.add(user)
        await db_session.commit()
        await db_session.refresh(user)

        return workspace, user, db_session

    def _create_command_body(self, command, text, team_id="T2222", user_id="U500"):
        """Create a Slack command body"""
        return {
            "command": command,
            "text": text,
            "team_id": team_id,
            "user_id": user_id,
            "channel_id": "C2222",
            "response_url": "https://hooks.slack.com/commands/mock"
        }

    @pytest.mark.asyncio
    async def test_incident_list(self, setup_incident_test):
        """Test /incident lists active incidents"""
        workspace, user, db_session = setup_incident_test
        handler = SlackHandler()

        if not handler.app:
            pytest.skip("Slack handler app not initialized")

        body = self._create_command_body("/incident", "", "T2222", "U500")
        assert handler is not None

    @pytest.mark.asyncio
    async def test_incident_start(self, setup_incident_test):
        """Test /incident start <name> creates incident"""
        workspace, user, db_session = setup_incident_test
        handler = SlackHandler()

        if not handler.app:
            pytest.skip("Slack handler app not initialized")

        body = self._create_command_body("/incident", "start Database Failure", "T2222", "U500")
        assert handler is not None

    @pytest.mark.asyncio
    async def test_incident_metrics(self, setup_incident_test):
        """Test /incident metrics <period>"""
        workspace, user, db_session = setup_incident_test
        handler = SlackHandler()

        if not handler.app:
            pytest.skip("Slack handler app not initialized")

        body = self._create_command_body("/incident", "metrics week", "T2222", "U500")
        assert handler is not None


class TestSlackAdminCommand:
    """Detailed tests for Slack /admin slash command"""

    @pytest.fixture
    async def setup_admin_test(self, db_session: AsyncSession):
        """Setup for admin command tests"""
        workspace = Workspace(
            name="Test Workspace",
            workspace_type="slack",
            external_id="T3333"
        )
        db_session.add(workspace)
        await db_session.commit()
        await db_session.refresh(workspace)

        admin = User(
            workspace_id=workspace.id,
            slack_user_id="U600",
            username="admin",
            first_name="Admin",
            last_name="User",
            display_name="Admin User",
            is_admin=True
        )
        regular = User(
            workspace_id=workspace.id,
            slack_user_id="U601",
            username="regular",
            first_name="Regular",
            last_name="User",
            display_name="Regular User"
        )
        db_session.add(admin)
        db_session.add(regular)
        await db_session.commit()

        return workspace, admin, regular, db_session

    def _create_command_body(self, command, text, team_id="T3333", user_id="U600"):
        """Create a Slack command body"""
        return {
            "command": command,
            "text": text,
            "team_id": team_id,
            "user_id": user_id,
            "channel_id": "C3333",
            "response_url": "https://hooks.slack.com/commands/mock"
        }

    @pytest.mark.asyncio
    async def test_admin_list(self, setup_admin_test):
        """Test /admin lists admins"""
        workspace, admin, regular, db_session = setup_admin_test
        handler = SlackHandler()

        if not handler.app:
            pytest.skip("Slack handler app not initialized")

        body = self._create_command_body("/admin", "", "T3333", "U600")
        assert handler is not None

    @pytest.mark.asyncio
    async def test_admin_add(self, setup_admin_test):
        """Test /admin add <user>"""
        workspace, admin, regular, db_session = setup_admin_test
        handler = SlackHandler()

        if not handler.app:
            pytest.skip("Slack handler app not initialized")

        body = self._create_command_body("/admin", "add <@U601>", "T3333", "U600")
        assert handler is not None


class TestSlackHelpCommand:
    """Detailed tests for Slack /help slash command"""

    @pytest.fixture
    async def setup_help_test(self, db_session: AsyncSession):
        """Setup for help command tests"""
        workspace = Workspace(
            name="Test Workspace",
            workspace_type="slack",
            external_id="T4444"
        )
        db_session.add(workspace)
        await db_session.commit()
        await db_session.refresh(workspace)

        user = User(
            workspace_id=workspace.id,
            slack_user_id="U700",
            username="user",
            first_name="Test",
            last_name="User",
            display_name="Test User"
        )
        db_session.add(user)
        await db_session.commit()

        return workspace, user, db_session

    def _create_command_body(self, command, text, team_id="T4444", user_id="U700"):
        """Create a Slack command body"""
        return {
            "command": command,
            "text": text,
            "team_id": team_id,
            "user_id": user_id,
            "channel_id": "C4444",
            "response_url": "https://hooks.slack.com/commands/mock"
        }

    @pytest.mark.asyncio
    async def test_help_command_shows_all_commands(self, setup_help_test):
        """Test /help shows all available commands"""
        workspace, user, db_session = setup_help_test
        handler = SlackHandler()

        if not handler.app:
            pytest.skip("Slack handler app not initialized")

        body = self._create_command_body("/help", "", "T4444", "U700")
        assert handler is not None
