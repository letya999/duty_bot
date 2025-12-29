import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from telegram import Update, User as TelegramUser, Chat, Message
from telegram.ext import ContextTypes
from app.handlers.telegram_handler import (
    TelegramHandler,
    get_or_create_telegram_workspace,
    format_telegram_text
)
from app.models import Workspace, User, Team, Schedule, Escalation
from app.commands.parser import CommandError


class TestTelegramHandler:
    """Test TelegramHandler message processing"""

    @pytest.fixture
    async def setup_handler(self, db_session: AsyncSession):
        """Setup Telegram handler with test data"""
        workspace = Workspace(
            name="Test Workspace",
            workspace_type="telegram",
            external_id="123456789"
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

        # Add UserAccount
        from app.models import UserAccount
        account = UserAccount(
            user_id=user.id,
            workspace_id=workspace.id,
            provider='telegram',
            provider_id='123456789',
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
        handler = TelegramHandler()
        return handler, workspace, user, team, db_session

    @pytest.fixture
    def mock_update(self):
        """Create a mock Telegram Update"""
        update = MagicMock(spec=Update)
        update.effective_user = MagicMock(spec=TelegramUser)
        update.effective_user.id = 123456789
        update.effective_user.username = "testuser"
        update.effective_user.first_name = "Test"
        update.effective_user.last_name = "User"

        update.effective_chat = MagicMock(spec=Chat)
        update.effective_chat.id = 123456789
        update.effective_chat.title = "Test Chat"

        update.effective_message = MagicMock(spec=Message)
        update.effective_message.reply_text = AsyncMock()

        return update

    @pytest.fixture
    def mock_context(self):
        """Create a mock Telegram context"""
        context = MagicMock(spec=ContextTypes.DEFAULT_TYPE)
        context.args = []
        return context

    @pytest.mark.asyncio
    async def test_handler_initialization(self):
        """Test handler initialization"""
        handler = TelegramHandler()
        assert handler is not None
        assert handler.app is None

    @pytest.mark.asyncio
    async def test_format_telegram_text(self):
        """Test format_telegram_text helper"""
        text = "Hello **bold** text"
        result = await format_telegram_text(text)
        assert isinstance(result, str)
        assert "Hello" in result

    @pytest.mark.asyncio
    async def test_get_or_create_telegram_workspace_new(self, db_session: AsyncSession):
        """Test creating new Telegram workspace"""
        workspace_id = await get_or_create_telegram_workspace(db_session, 999, "New Chat")

        assert workspace_id is not None
        assert isinstance(workspace_id, int)

    @pytest.mark.asyncio
    async def test_get_or_create_telegram_workspace_existing(self, db_session: AsyncSession, setup_handler):
        """Test getting existing Telegram workspace"""
        handler, workspace, user, team, db = setup_handler

        workspace_id = await get_or_create_telegram_workspace(db, int(workspace.external_id), "Test Chat")

        assert workspace_id == workspace.id

    @pytest.mark.asyncio
    async def test_get_workspace_and_user(self, db_session: AsyncSession, setup_handler, mock_update):
        """Test _get_workspace_and_user helper"""
        handler, workspace, user, team, db = setup_handler

        workspace_id, retrieved_user = await handler._get_workspace_and_user(mock_update, db_session)

        assert workspace_id is not None
        assert retrieved_user is not None
        assert retrieved_user.username == mock_update.effective_user.username

    @pytest.mark.asyncio
    async def test_duty_command_no_args(self, db_session: AsyncSession, setup_handler, mock_update, mock_context):
        """Test /duty command with no arguments"""
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

        mock_context.args = []

        with patch('app.handlers.telegram_handler.get_db_with_retry') as mock_db:
            mock_db.return_value.__aenter__.return_value = db_session
            await handler.duty_command(mock_update, mock_context)

        mock_update.effective_message.reply_text.assert_called_once()

    @pytest.mark.asyncio
    async def test_duty_command_with_team_arg(self, db_session: AsyncSession, setup_handler, mock_update, mock_context):
        """Test /duty command with team argument"""
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

        mock_context.args = ["backend"]

        with patch('app.handlers.telegram_handler.get_db_with_retry') as mock_db:
            mock_db.return_value.__aenter__.return_value = db_session
            await handler.duty_command(mock_update, mock_context)

        mock_update.effective_message.reply_text.assert_called_once()

    @pytest.mark.asyncio
    async def test_duty_command_team_not_found(self, db_session: AsyncSession, setup_handler, mock_update, mock_context):
        """Test /duty command with non-existent team"""
        handler, workspace, user, team, db = setup_handler

        mock_context.args = ["nonexistent"]

        with patch('app.handlers.telegram_handler.get_db_with_retry') as mock_db:
            mock_db.return_value.__aenter__.return_value = db_session
            await handler.duty_command(mock_update, mock_context)

        mock_update.effective_message.reply_text.assert_called_once()
        call_args = mock_update.effective_message.reply_text.call_args[0][0]
        assert "not found" in call_args.lower() or "error" in call_args.lower()

    @pytest.mark.asyncio
    async def test_team_command_list(self, db_session: AsyncSession, setup_handler, mock_update, mock_context):
        """Test /team command to list teams"""
        handler, workspace, user, team, db = setup_handler

        mock_context.args = []

        with patch('app.handlers.telegram_handler.get_db_with_retry') as mock_db:
            mock_db.return_value.__aenter__.return_value = db_session
            await handler.team_command(mock_update, mock_context)

        mock_update.effective_message.reply_text.assert_called_once()

    @pytest.mark.asyncio
    async def test_team_command_add(self, db_session: AsyncSession, setup_handler, mock_update, mock_context):
        """Test /team add command"""
        handler, workspace, user, team, db = setup_handler

        # Make user admin
        user.is_admin = True
        db_session.add(user)
        await db_session.commit()

        mock_context.args = ["add", "frontend", '"Frontend Team"']

        with patch('app.handlers.telegram_handler.get_db_with_retry') as mock_db:
            mock_db.return_value.__aenter__.return_value = db_session
            await handler.team_command(mock_update, mock_context)

        mock_update.effective_message.reply_text.assert_called_once()

    @pytest.mark.asyncio
    async def test_team_info_command(self, db_session: AsyncSession, setup_handler, mock_update, mock_context):
        """Test /team <team_name> command"""
        handler, workspace, user, team, db = setup_handler

        mock_context.args = ["backend"]

        with patch('app.handlers.telegram_handler.get_db_with_retry') as mock_db:
            mock_db.return_value.__aenter__.return_value = db_session
            await handler.team_command(mock_update, mock_context)

        mock_update.effective_message.reply_text.assert_called_once()

    @pytest.mark.asyncio
    async def test_schedule_command(self, db_session: AsyncSession, setup_handler, mock_update, mock_context):
        """Test /schedule command"""
        handler, workspace, user, team, db = setup_handler

        mock_context.args = ["backend"]

        with patch('app.handlers.telegram_handler.get_db_with_retry') as mock_db:
            mock_db.return_value.__aenter__.return_value = db_session
            await handler.schedule_command(mock_update, mock_context)

        mock_update.effective_message.reply_text.assert_called_once()

    @pytest.mark.asyncio
    async def test_shift_command(self, db_session: AsyncSession, setup_handler, mock_update, mock_context):
        """Test /shift command"""
        handler, workspace, user, team, db = setup_handler

        mock_context.args = ["backend"]

        with patch('app.handlers.telegram_handler.get_db_with_retry') as mock_db:
            mock_db.return_value.__aenter__.return_value = db_session
            await handler.shift_command(mock_update, mock_context)

        mock_update.effective_message.reply_text.assert_called_once()

    @pytest.mark.asyncio
    async def test_escalation_command(self, db_session: AsyncSession, setup_handler, mock_update, mock_context):
        """Test /escalation command"""
        handler, workspace, user, team, db = setup_handler

        mock_context.args = []

        with patch('app.handlers.telegram_handler.get_db_with_retry') as mock_db:
            mock_db.return_value.__aenter__.return_value = db_session
            await handler.escalation_command(mock_update, mock_context)

        mock_update.effective_message.reply_text.assert_called_once()

    @pytest.mark.asyncio
    async def test_escalate_command(self, db_session: AsyncSession, setup_handler, mock_update, mock_context):
        """Test /escalate command"""
        handler, workspace, user, team, db = setup_handler

        # Set up escalation
        escalation = Escalation(
            team_id=team.id,
            cto_id=user.id
        )
        db_session.add(escalation)
        await db_session.commit()

        mock_context.args = ["backend"]

        with patch('app.handlers.telegram_handler.get_db_with_retry') as mock_db:
            mock_db.return_value.__aenter__.return_value = db_session
            await handler.escalate_command(mock_update, mock_context)

        mock_update.effective_message.reply_text.assert_called_once()

    @pytest.mark.asyncio
    async def test_incident_command_list(self, db_session: AsyncSession, setup_handler, mock_update, mock_context):
        """Test /incident command to list incidents"""
        handler, workspace, user, team, db = setup_handler

        mock_context.args = []

        with patch('app.handlers.telegram_handler.get_db_with_retry') as mock_db:
            mock_db.return_value.__aenter__.return_value = db_session
            await handler.incident_command(mock_update, mock_context)

        mock_update.effective_message.reply_text.assert_called_once()

    @pytest.mark.asyncio
    async def test_incident_start_command(self, db_session: AsyncSession, setup_handler, mock_update, mock_context):
        """Test /incident start command"""
        handler, workspace, user, team, db = setup_handler

        mock_context.args = ["start", "Database", "failure"]

        with patch('app.handlers.telegram_handler.get_db_with_retry') as mock_db:
            mock_db.return_value.__aenter__.return_value = db_session
            await handler.incident_command(mock_update, mock_context)

        mock_update.effective_message.reply_text.assert_called_once()

    @pytest.mark.asyncio
    async def test_admin_command(self, db_session: AsyncSession, setup_handler, mock_update, mock_context):
        """Test /admin command"""
        handler, workspace, user, team, db = setup_handler

        # Make user admin
        user.is_admin = True
        db_session.add(user)
        await db_session.commit()

        mock_context.args = []

        with patch('app.handlers.telegram_handler.get_db_with_retry') as mock_db:
            mock_db.return_value.__aenter__.return_value = db_session
            await handler.admin_command(mock_update, mock_context)

        mock_update.effective_message.reply_text.assert_called_once()

    @pytest.mark.asyncio
    async def test_help_command(self, db_session: AsyncSession, setup_handler, mock_update, mock_context):
        """Test /help command"""
        handler, workspace, user, team, db = setup_handler

        mock_context.args = []

        with patch('app.handlers.telegram_handler.get_db_with_retry') as mock_db:
            mock_db.return_value.__aenter__.return_value = db_session
            await handler.help_command(mock_update, mock_context)

        mock_update.effective_message.reply_text.assert_called_once()
        call_args = mock_update.effective_message.reply_text.call_args[0][0]
        assert "Available Commands" in call_args

    @pytest.mark.asyncio
    async def test_command_error_handling(self, db_session: AsyncSession, setup_handler, mock_update, mock_context):
        """Test command error handling"""
        handler, workspace, user, team, db = setup_handler

        # Try invalid team
        mock_context.args = ["nonexistent"]

        with patch('app.handlers.telegram_handler.get_db_with_retry') as mock_db:
            mock_db.return_value.__aenter__.return_value = db_session
            await handler.duty_command(mock_update, mock_context)

        # Should have called reply_text with error message
        mock_update.effective_message.reply_text.assert_called_once()

    @pytest.mark.asyncio
    async def test_workspace_creation(self, db_session: AsyncSession, setup_handler):
        """Test workspace creation from Telegram group"""
        handler, workspace, user, team, db = setup_handler

        assert workspace.workspace_type == "telegram"
        assert workspace.external_id is not None
        assert workspace.external_id == "123456789"

    @pytest.mark.asyncio
    async def test_user_creation(self, db_session: AsyncSession, setup_handler):
        """Test user creation from Telegram message"""
        handler, workspace, user, team, db = setup_handler

        assert user.username is not None
        assert user.workspace_id == workspace.id
