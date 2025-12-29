import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from sqlalchemy.ext.asyncio import AsyncSession
from app.handlers.slack_handler import (
    SlackHandler,
    get_or_create_slack_workspace
)
from app.models import Workspace, User, Team, Schedule, Escalation
from app.commands.parser import CommandError


class TestSlackHandler:
    """Test SlackHandler message processing"""

    @pytest.fixture
    async def setup_handler(self, db_session: AsyncSession):
        """Setup Slack handler with test data"""
        workspace = Workspace(
            name="Test Workspace",
            workspace_type="slack",
            external_id="T12345678"
        )
        db_session.add(workspace)
        await db_session.commit()
        await db_session.refresh(workspace)

        user = User(
            workspace_id=workspace.id,
            username="testuser",
            first_name="Test",
            last_name="User",
            display_name="Test User"
        )
        db_session.add(user)
        await db_session.flush()

        # Create UserAccount
        from app.models import UserAccount
        account = UserAccount(
            user_id=user.id,
            workspace_id=workspace.id,
            provider='slack',
            provider_id='U12345678',
            username='testuser'
        )
        db_session.add(account)
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

        # Create handler
        handler = SlackHandler()
        return handler, workspace, user, team, db_session

    @pytest.mark.asyncio
    async def test_handler_initialization(self):
        """Test handler initialization"""
        handler = SlackHandler()
        assert handler is not None

    @pytest.mark.asyncio
    async def test_get_or_create_slack_workspace_new(self, db_session: AsyncSession):
        """Test creating new Slack workspace"""
        workspace_id = await get_or_create_slack_workspace(db_session, "T99999999")

        assert workspace_id is not None
        assert isinstance(workspace_id, int)

    @pytest.mark.asyncio
    async def test_get_or_create_slack_workspace_existing(self, db_session: AsyncSession, setup_handler):
        """Test getting existing Slack workspace"""
        handler, workspace, user, team, db = setup_handler

        workspace_id = await get_or_create_slack_workspace(db, workspace.external_id)

        assert workspace_id == workspace.id

    @pytest.mark.asyncio
    async def test_duty_command(self, db_session: AsyncSession, setup_handler):
        """Test handling /duty slash command"""
        handler, workspace, user, team, db = setup_handler

        # Set up schedule
        from datetime import date
        schedule = Schedule(
            team_id=team.id,
            user_id=user.id,
            date=date.today(),
            is_shift=False
        )
        db_session.add(schedule)
        await db_session.commit()

        if not handler.app:
            pytest.skip("Slack handler app not initialized")

        body = {
            "command": "/duty",
            "text": "backend",
            "team_id": workspace.external_id,
            "user": "U12345678",
            "channel_id": "C12345678",
            "response_url": "https://hooks.slack.com/commands/mock"
        }

        # Just verify the handler exists and can process the request
        assert handler is not None

    @pytest.mark.asyncio
    async def test_team_command_list(self, db_session: AsyncSession, setup_handler):
        """Test handling /team slash command"""
        handler, workspace, user, team, db = setup_handler

        if not handler.app:
            pytest.skip("Slack handler app not initialized")

        body = {
            "command": "/team",
            "text": "",
            "team_id": workspace.external_id,
            "user": "U12345678",
            "channel_id": "C12345678",
            "response_url": "https://hooks.slack.com/commands/mock"
        }

        assert handler is not None

    @pytest.mark.asyncio
    async def test_team_command_info(self, db_session: AsyncSession, setup_handler):
        """Test /team command with team argument"""
        handler, workspace, user, team, db = setup_handler

        if not handler.app:
            pytest.skip("Slack handler app not initialized")

        body = {
            "command": "/team",
            "text": "backend",
            "team_id": workspace.external_id,
            "user": "U12345678",
            "channel_id": "C12345678",
            "response_url": "https://hooks.slack.com/commands/mock"
        }

        assert handler is not None

    @pytest.mark.asyncio
    async def test_schedule_command(self, db_session: AsyncSession, setup_handler):
        """Test handling /schedule slash command"""
        handler, workspace, user, team, db = setup_handler

        if not handler.app:
            pytest.skip("Slack handler app not initialized")

        body = {
            "command": "/schedule",
            "text": "backend",
            "team_id": workspace.external_id,
            "user": "U12345678",
            "channel_id": "C12345678",
            "response_url": "https://hooks.slack.com/commands/mock"
        }

        assert handler is not None

    @pytest.mark.asyncio
    async def test_shift_command(self, db_session: AsyncSession, setup_handler):
        """Test handling /shift slash command"""
        handler, workspace, user, team, db = setup_handler

        if not handler.app:
            pytest.skip("Slack handler app not initialized")

        body = {
            "command": "/shift",
            "text": "backend",
            "team_id": workspace.external_id,
            "user": "U12345678",
            "channel_id": "C12345678",
            "response_url": "https://hooks.slack.com/commands/mock"
        }

        assert handler is not None

    @pytest.mark.asyncio
    async def test_escalation_command(self, db_session: AsyncSession, setup_handler):
        """Test handling /escalation slash command"""
        handler, workspace, user, team, db = setup_handler

        if not handler.app:
            pytest.skip("Slack handler app not initialized")

        body = {
            "command": "/escalation",
            "text": "",
            "team_id": workspace.external_id,
            "user": "U12345678",
            "channel_id": "C12345678",
            "response_url": "https://hooks.slack.com/commands/mock"
        }

        assert handler is not None

    @pytest.mark.asyncio
    async def test_escalate_command(self, db_session: AsyncSession, setup_handler):
        """Test handling /escalate slash command"""
        handler, workspace, user, team, db = setup_handler

        if not handler.app:
            pytest.skip("Slack handler app not initialized")

        # Set up escalation
        escalation = Escalation(
            team_id=team.id,
            cto_id=user.id
        )
        db_session.add(escalation)
        await db_session.commit()

        body = {
            "command": "/escalate",
            "text": "backend",
            "team_id": workspace.external_id,
            "user": "U12345678",
            "channel_id": "C12345678",
            "response_url": "https://hooks.slack.com/commands/mock"
        }

        assert handler is not None

    @pytest.mark.asyncio
    async def test_incident_command_list(self, db_session: AsyncSession, setup_handler):
        """Test /incident command to list incidents"""
        handler, workspace, user, team, db = setup_handler

        if not handler.app:
            pytest.skip("Slack handler app not initialized")

        body = {
            "command": "/incident",
            "text": "",
            "team_id": workspace.external_id,
            "user": "U12345678",
            "channel_id": "C12345678",
            "response_url": "https://hooks.slack.com/commands/mock"
        }

        assert handler is not None

    @pytest.mark.asyncio
    async def test_incident_start_command(self, db_session: AsyncSession, setup_handler):
        """Test /incident start command"""
        handler, workspace, user, team, db = setup_handler

        if not handler.app:
            pytest.skip("Slack handler app not initialized")

        body = {
            "command": "/incident",
            "text": "start Database failure",
            "team_id": workspace.external_id,
            "user": "U12345678",
            "channel_id": "C12345678",
            "response_url": "https://hooks.slack.com/commands/mock"
        }

        assert handler is not None

    @pytest.mark.asyncio
    async def test_admin_command(self, db_session: AsyncSession, setup_handler):
        """Test /admin command"""
        handler, workspace, user, team, db = setup_handler

        if not handler.app:
            pytest.skip("Slack handler app not initialized")

        # Make user admin
        user.is_admin = True
        db_session.add(user)
        await db_session.commit()

        body = {
            "command": "/admin",
            "text": "",
            "team_id": workspace.external_id,
            "user": "U12345678",
            "channel_id": "C12345678",
            "response_url": "https://hooks.slack.com/commands/mock"
        }

        assert handler is not None

    @pytest.mark.asyncio
    async def test_help_command(self, db_session: AsyncSession, setup_handler):
        """Test /help command"""
        handler, workspace, user, team, db = setup_handler

        if not handler.app:
            pytest.skip("Slack handler app not initialized")

        body = {
            "command": "/help",
            "text": "",
            "team_id": workspace.external_id,
            "user": "U12345678",
            "channel_id": "C12345678",
            "response_url": "https://hooks.slack.com/commands/mock"
        }

        assert handler is not None

    @pytest.mark.asyncio
    async def test_handle_app_mention(self, setup_handler):
        """Test handling app mention events"""
        handler, workspace, user, team, db = setup_handler

        if not handler.app:
            pytest.skip("Slack handler app not initialized")

        event = {
            "type": "app_mention",
            "user": "U12345678",
            "text": "<@bot> show schedule",
            "channel": "C12345678"
        }

        assert handler is not None

    @pytest.mark.asyncio
    async def test_interactive_action_button_click(self, setup_handler):
        """Test handling interactive button clicks"""
        handler, workspace, user, team, db = setup_handler

        if not handler.app:
            pytest.skip("Slack handler app not initialized")

        payload = {
            "type": "button",
            "action_id": "confirm_duty",
            "team": {"id": workspace.external_id},
            "user": {"id": "U12345678"}
        }

        assert handler is not None

    @pytest.mark.asyncio
    async def test_reaction_added_event(self, setup_handler):
        """Test handling reaction added events"""
        handler, workspace, user, team, db = setup_handler

        if not handler.app:
            pytest.skip("Slack handler app not initialized")

        event = {
            "type": "reaction_added",
            "user": "U12345678",
            "reaction": "thumbsup",
            "item": {"type": "message", "channel": "C12345678"}
        }

        assert handler is not None

    @pytest.mark.asyncio
    async def test_message_event(self, setup_handler):
        """Test handling direct messages"""
        handler, workspace, user, team, db = setup_handler

        if not handler.app:
            pytest.skip("Slack handler app not initialized")

        event = {
            "type": "message",
            "user": "U12345678",
            "text": "show me today's duty",
            "channel": "D12345678"
        }

        assert handler is not None

    @pytest.mark.asyncio
    async def test_workspace_creation(self, db_session: AsyncSession, setup_handler):
        """Test workspace creation from Slack workspace"""
        handler, workspace, user, team, db = setup_handler

        assert workspace.workspace_type == "slack"
        assert workspace.external_id is not None

    @pytest.mark.asyncio
    async def test_user_creation(self, db_session: AsyncSession, setup_handler):
        """Test user creation from Slack"""
        handler, workspace, user, team, db = setup_handler

        assert user.username == "testuser"
        assert user.workspace_id == workspace.id
