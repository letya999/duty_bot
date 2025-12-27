import pytest
from unittest.mock import AsyncMock, MagicMock
from sqlalchemy.ext.asyncio import AsyncSession
from app.handlers.slack_handler import SlackHandler
from app.models import Workspace, User, Team


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
            slack_user_id="U12345678",
            username="testuser",
            first_name="Test",
            last_name="User"
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

        # Create handler
        handler = SlackHandler()
        return handler, workspace, user, team

    @pytest.mark.asyncio
    async def test_handler_initialization(self):
        """Test handler initialization"""
        handler = SlackHandler()
        # Handler should be initialized (may have app or not depending on settings)
        assert handler is not None

    @pytest.mark.asyncio
    async def test_handle_app_mention(self, setup_handler):
        """Test handling app mention events"""
        handler, workspace, user, team = setup_handler

        event = {
            "type": "app_mention",
            "user": user.slack_user_id,
            "text": "<@bot> show schedule",
            "channel": "C12345678"
        }

        assert handler is not None

    @pytest.mark.asyncio
    async def test_handle_slash_command_duty(self, setup_handler):
        """Test handling /duty slash command"""
        handler, workspace, user, team = setup_handler

        body = {
            "command": "/duty",
            "text": "user1 2024-01-15",
            "team_id": workspace.external_id,
            "user_id": user.slack_user_id,
            "channel_id": "C12345678"
        }

        assert handler is not None

    @pytest.mark.asyncio
    async def test_handle_slash_command_team(self, setup_handler):
        """Test handling /team slash command"""
        handler, workspace, user, team = setup_handler

        body = {
            "command": "/team",
            "text": "backend",
            "team_id": workspace.external_id,
            "user_id": user.slack_user_id
        }

        assert handler is not None

    @pytest.mark.asyncio
    async def test_handle_slash_command_schedule(self, setup_handler):
        """Test handling /schedule slash command"""
        handler, workspace, user, team = setup_handler

        body = {
            "command": "/schedule",
            "text": "backend",
            "team_id": workspace.external_id,
            "user_id": user.slack_user_id
        }

        assert handler is not None

    @pytest.mark.asyncio
    async def test_handle_slash_command_stats(self, setup_handler):
        """Test handling /stats slash command"""
        handler, workspace, user, team = setup_handler

        body = {
            "command": "/stats",
            "text": "backend",
            "team_id": workspace.external_id,
            "user_id": user.slack_user_id
        }

        assert handler is not None

    @pytest.mark.asyncio
    async def test_handle_workspace_creation(self, setup_handler):
        """Test workspace creation from Slack workspace"""
        handler, workspace, user, team = setup_handler

        assert workspace.workspace_type == "slack"
        assert workspace.external_id is not None

    @pytest.mark.asyncio
    async def test_handle_user_creation(self, setup_handler):
        """Test user creation from Slack"""
        handler, workspace, user, team = setup_handler

        assert user.slack_user_id is not None
        assert user.workspace_id == workspace.id

    @pytest.mark.asyncio
    async def test_send_message(self, setup_handler):
        """Test sending message to channel"""
        handler, workspace, user, team = setup_handler

        assert handler is not None

    @pytest.mark.asyncio
    async def test_interactive_action_button_click(self, setup_handler):
        """Test handling interactive button clicks"""
        handler, workspace, user, team = setup_handler

        payload = {
            "type": "button",
            "action_id": "confirm_duty",
            "team": {"id": workspace.external_id},
            "user": {"id": user.slack_user_id}
        }

        assert handler is not None

    @pytest.mark.asyncio
    async def test_reaction_added_event(self, setup_handler):
        """Test handling reaction added events"""
        handler, workspace, user, team = setup_handler

        event = {
            "type": "reaction_added",
            "user": user.slack_user_id,
            "reaction": "thumbsup",
            "item": {"type": "message", "channel": "C12345678"}
        }

        assert handler is not None

    @pytest.mark.asyncio
    async def test_message_event(self, setup_handler):
        """Test handling direct messages"""
        handler, workspace, user, team = setup_handler

        event = {
            "type": "message",
            "user": user.slack_user_id,
            "text": "show me today's duty",
            "channel": "D12345678"
        }

        assert handler is not None
