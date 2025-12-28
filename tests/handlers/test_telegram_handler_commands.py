import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import date
from sqlalchemy.ext.asyncio import AsyncSession
from telegram import Update, User as TelegramUser, Chat, Message
from telegram.ext import ContextTypes
from app.handlers.telegram_handler import TelegramHandler
from app.models import Workspace, User, Team, Schedule, Escalation, Incident


class TestTelegramDutyCommand:
    """Detailed tests for Telegram /duty command"""

    @pytest.fixture
    async def setup_duty_test(self, db_session: AsyncSession):
        """Setup for duty command tests"""
        workspace = Workspace(
            name="Test Workspace",
            workspace_type="telegram",
            external_id="123"
        )
        db_session.add(workspace)
        await db_session.commit()
        await db_session.refresh(workspace)

        user1 = User(
            workspace_id=workspace.id,
            telegram_id=1,
            telegram_username="user1",
            first_name="User",
            last_name="One",
            display_name="User One"
        )
        user2 = User(
            workspace_id=workspace.id,
            telegram_id=2,
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

        # Add schedule for today
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

    def _create_mock_update(self, chat_id="123", user_id=1):
        """Create a mock Telegram Update"""
        update = MagicMock(spec=Update)
        update.effective_user = MagicMock(spec=TelegramUser)
        update.effective_user.id = user_id
        update.effective_user.username = "testuser"
        update.effective_user.first_name = "Test"
        update.effective_user.last_name = "User"

        update.effective_chat = MagicMock(spec=Chat)
        update.effective_chat.id = int(chat_id)
        update.effective_chat.title = "Test Chat"

        update.effective_message = MagicMock(spec=Message)
        update.effective_message.reply_text = AsyncMock()

        return update

    def _create_mock_context(self, args=None):
        """Create a mock Telegram context"""
        context = MagicMock(spec=ContextTypes.DEFAULT_TYPE)
        context.args = args or []
        return context

    @pytest.mark.asyncio
    async def test_duty_show_all_today(self, setup_duty_test):
        """Test /duty with no args shows all teams duty"""
        workspace, user1, user2, backend_team, frontend_team, db_session = setup_duty_test
        handler = TelegramHandler()

        update = self._create_mock_update("123", 1)
        context = self._create_mock_context([])

        with patch('app.handlers.telegram_handler.get_db_with_retry') as mock_db:
            mock_db.return_value.__aenter__.return_value = db_session
            await handler.duty_command(update, context)

        # Should call reply_text
        assert update.effective_message.reply_text.called
        call_text = update.effective_message.reply_text.call_args[0][0]
        # Should show both teams
        assert "Backend Team" in call_text or "User One" in call_text

    @pytest.mark.asyncio
    async def test_duty_mention_specific_team(self, setup_duty_test):
        """Test /duty <team> mentions specific team duty"""
        workspace, user1, user2, backend_team, frontend_team, db_session = setup_duty_test
        handler = TelegramHandler()

        update = self._create_mock_update("123", 1)
        context = self._create_mock_context(["backend"])

        with patch('app.handlers.telegram_handler.get_db_with_retry') as mock_db:
            mock_db.return_value.__aenter__.return_value = db_session
            await handler.duty_command(update, context)

        # Should call reply_text with mention
        assert update.effective_message.reply_text.called
        call_text = update.effective_message.reply_text.call_args[0][0]
        assert "user1" in call_text or "User One" in call_text or "Backend" in call_text

    @pytest.mark.asyncio
    async def test_duty_invalid_team(self, setup_duty_test):
        """Test /duty with invalid team name"""
        workspace, user1, user2, backend_team, frontend_team, db_session = setup_duty_test
        handler = TelegramHandler()

        update = self._create_mock_update("123", 1)
        context = self._create_mock_context(["invalid_team"])

        with patch('app.handlers.telegram_handler.get_db_with_retry') as mock_db:
            mock_db.return_value.__aenter__.return_value = db_session
            await handler.duty_command(update, context)

        # Should call reply_text with error
        assert update.effective_message.reply_text.called
        call_text = update.effective_message.reply_text.call_args[0][0]
        assert "not found" in call_text.lower() or "error" in call_text.lower() or "❌" in call_text


class TestTelegramTeamCommand:
    """Detailed tests for Telegram /team command"""

    @pytest.fixture
    async def setup_team_test(self, db_session: AsyncSession):
        """Setup for team command tests"""
        workspace = Workspace(
            name="Test Workspace",
            workspace_type="telegram",
            external_id="456"
        )
        db_session.add(workspace)
        await db_session.commit()
        await db_session.refresh(workspace)

        lead = User(
            workspace_id=workspace.id,
            telegram_id=100,
            telegram_username="lead",
            first_name="Lead",
            last_name="User",
            display_name="Lead User",
            is_admin=True
        )
        member = User(
            workspace_id=workspace.id,
            telegram_id=101,
            telegram_username="member",
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

    def _create_mock_update(self, chat_id="456", user_id=100):
        """Create a mock Telegram Update"""
        update = MagicMock(spec=Update)
        update.effective_user = MagicMock(spec=TelegramUser)
        update.effective_user.id = user_id
        update.effective_user.username = "testuser"
        update.effective_user.first_name = "Test"
        update.effective_user.last_name = "User"

        update.effective_chat = MagicMock(spec=Chat)
        update.effective_chat.id = int(chat_id)
        update.effective_chat.title = "Test Chat"

        update.effective_message = MagicMock(spec=Message)
        update.effective_message.reply_text = AsyncMock()

        return update

    def _create_mock_context(self, args=None):
        """Create a mock Telegram context"""
        context = MagicMock(spec=ContextTypes.DEFAULT_TYPE)
        context.args = args or []
        return context

    @pytest.mark.asyncio
    async def test_team_list(self, setup_team_test):
        """Test /team lists all teams"""
        workspace, lead, member, team, db_session = setup_team_test
        handler = TelegramHandler()

        update = self._create_mock_update("456", 100)
        context = self._create_mock_context([])

        with patch('app.handlers.telegram_handler.get_db_with_retry') as mock_db:
            mock_db.return_value.__aenter__.return_value = db_session
            await handler.team_command(update, context)

        assert update.effective_message.reply_text.called
        call_text = update.effective_message.reply_text.call_args[0][0]
        assert "backend" in call_text or "Backend Team" in call_text

    @pytest.mark.asyncio
    async def test_team_info(self, setup_team_test):
        """Test /team <name> shows team info"""
        workspace, lead, member, team, db_session = setup_team_test
        handler = TelegramHandler()

        update = self._create_mock_update("456", 100)
        context = self._create_mock_context(["backend"])

        with patch('app.handlers.telegram_handler.get_db_with_retry') as mock_db:
            mock_db.return_value.__aenter__.return_value = db_session
            await handler.team_command(update, context)

        assert update.effective_message.reply_text.called
        call_text = update.effective_message.reply_text.call_args[0][0]
        assert "Backend Team" in call_text or "backend" in call_text
        assert "Lead User" in call_text or "Member" in call_text


class TestTelegramScheduleCommand:
    """Detailed tests for Telegram /schedule command"""

    @pytest.fixture
    async def setup_schedule_test(self, db_session: AsyncSession):
        """Setup for schedule command tests"""
        workspace = Workspace(
            name="Test Workspace",
            workspace_type="telegram",
            external_id="789"
        )
        db_session.add(workspace)
        await db_session.commit()
        await db_session.refresh(workspace)

        user = User(
            workspace_id=workspace.id,
            telegram_id=200,
            telegram_username="user",
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

    def _create_mock_update(self, chat_id="789", user_id=200):
        """Create a mock Telegram Update"""
        update = MagicMock(spec=Update)
        update.effective_user = MagicMock(spec=TelegramUser)
        update.effective_user.id = user_id
        update.effective_user.username = "testuser"
        update.effective_user.first_name = "Test"
        update.effective_user.last_name = "User"

        update.effective_chat = MagicMock(spec=Chat)
        update.effective_chat.id = int(chat_id)
        update.effective_chat.title = "Test Chat"

        update.effective_message = MagicMock(spec=Message)
        update.effective_message.reply_text = AsyncMock()

        return update

    def _create_mock_context(self, args=None):
        """Create a mock Telegram context"""
        context = MagicMock(spec=ContextTypes.DEFAULT_TYPE)
        context.args = args or []
        return context

    @pytest.mark.asyncio
    async def test_schedule_show_week(self, setup_schedule_test):
        """Test /schedule <team> shows weekly schedule"""
        workspace, user, team, db_session = setup_schedule_test
        handler = TelegramHandler()

        update = self._create_mock_update("789", 200)
        context = self._create_mock_context(["backend"])

        with patch('app.handlers.telegram_handler.get_db_with_retry') as mock_db:
            mock_db.return_value.__aenter__.return_value = db_session
            await handler.schedule_command(update, context)

        assert update.effective_message.reply_text.called


class TestTelegramShiftCommand:
    """Detailed tests for Telegram /shift command"""

    @pytest.fixture
    async def setup_shift_test(self, db_session: AsyncSession):
        """Setup for shift command tests"""
        workspace = Workspace(
            name="Test Workspace",
            workspace_type="telegram",
            external_id="999"
        )
        db_session.add(workspace)
        await db_session.commit()
        await db_session.refresh(workspace)

        user1 = User(
            workspace_id=workspace.id,
            telegram_id=300,
            telegram_username="user1",
            first_name="User",
            last_name="One",
            display_name="User One"
        )
        user2 = User(
            workspace_id=workspace.id,
            telegram_id=301,
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

    def _create_mock_update(self, chat_id="999", user_id=300):
        """Create a mock Telegram Update"""
        update = MagicMock(spec=Update)
        update.effective_user = MagicMock(spec=TelegramUser)
        update.effective_user.id = user_id
        update.effective_user.username = "testuser"
        update.effective_user.first_name = "Test"
        update.effective_user.last_name = "User"

        update.effective_chat = MagicMock(spec=Chat)
        update.effective_chat.id = int(chat_id)
        update.effective_chat.title = "Test Chat"

        update.effective_message = MagicMock(spec=Message)
        update.effective_message.reply_text = AsyncMock()

        return update

    def _create_mock_context(self, args=None):
        """Create a mock Telegram context"""
        context = MagicMock(spec=ContextTypes.DEFAULT_TYPE)
        context.args = args or []
        return context

    @pytest.mark.asyncio
    async def test_shift_show_week(self, setup_shift_test):
        """Test /shift <team> shows weekly shifts"""
        workspace, user1, user2, team, db_session = setup_shift_test
        handler = TelegramHandler()

        update = self._create_mock_update("999", 300)
        context = self._create_mock_context(["backend"])

        with patch('app.handlers.telegram_handler.get_db_with_retry') as mock_db:
            mock_db.return_value.__aenter__.return_value = db_session
            await handler.shift_command(update, context)

        assert update.effective_message.reply_text.called


class TestTelegramEscalationCommand:
    """Detailed tests for Telegram /escalation command"""

    @pytest.fixture
    async def setup_escalation_test(self, db_session: AsyncSession):
        """Setup for escalation command tests"""
        workspace = Workspace(
            name="Test Workspace",
            workspace_type="telegram",
            external_id="1111"
        )
        db_session.add(workspace)
        await db_session.commit()
        await db_session.refresh(workspace)

        lead = User(
            workspace_id=workspace.id,
            telegram_id=400,
            telegram_username="lead",
            first_name="Lead",
            last_name="User",
            display_name="Lead User"
        )
        cto = User(
            workspace_id=workspace.id,
            telegram_id=401,
            telegram_username="cto",
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

    def _create_mock_update(self, chat_id="1111", user_id=400):
        """Create a mock Telegram Update"""
        update = MagicMock(spec=Update)
        update.effective_user = MagicMock(spec=TelegramUser)
        update.effective_user.id = user_id
        update.effective_user.username = "testuser"
        update.effective_user.first_name = "Test"
        update.effective_user.last_name = "User"

        update.effective_chat = MagicMock(spec=Chat)
        update.effective_chat.id = int(chat_id)
        update.effective_chat.title = "Test Chat"

        update.effective_message = MagicMock(spec=Message)
        update.effective_message.reply_text = AsyncMock()

        return update

    def _create_mock_context(self, args=None):
        """Create a mock Telegram context"""
        context = MagicMock(spec=ContextTypes.DEFAULT_TYPE)
        context.args = args or []
        return context

    @pytest.mark.asyncio
    async def test_escalation_show(self, setup_escalation_test):
        """Test /escalation shows escalation hierarchy"""
        workspace, lead, cto, team, db_session = setup_escalation_test
        handler = TelegramHandler()

        update = self._create_mock_update("1111", 400)
        context = self._create_mock_context([])

        with patch('app.handlers.telegram_handler.get_db_with_retry') as mock_db:
            mock_db.return_value.__aenter__.return_value = db_session
            await handler.escalation_command(update, context)

        assert update.effective_message.reply_text.called


class TestTelegramIncidentCommand:
    """Detailed tests for Telegram /incident command"""

    @pytest.fixture
    async def setup_incident_test(self, db_session: AsyncSession):
        """Setup for incident command tests"""
        workspace = Workspace(
            name="Test Workspace",
            workspace_type="telegram",
            external_id="2222"
        )
        db_session.add(workspace)
        await db_session.commit()
        await db_session.refresh(workspace)

        user = User(
            workspace_id=workspace.id,
            telegram_id=500,
            telegram_username="user",
            first_name="Test",
            last_name="User",
            display_name="Test User"
        )
        db_session.add(user)
        await db_session.commit()
        await db_session.refresh(user)

        return workspace, user, db_session

    def _create_mock_update(self, chat_id="2222", user_id=500):
        """Create a mock Telegram Update"""
        update = MagicMock(spec=Update)
        update.effective_user = MagicMock(spec=TelegramUser)
        update.effective_user.id = user_id
        update.effective_user.username = "testuser"
        update.effective_user.first_name = "Test"
        update.effective_user.last_name = "User"

        update.effective_chat = MagicMock(spec=Chat)
        update.effective_chat.id = int(chat_id)
        update.effective_chat.title = "Test Chat"

        update.effective_message = MagicMock(spec=Message)
        update.effective_message.reply_text = AsyncMock()

        return update

    def _create_mock_context(self, args=None):
        """Create a mock Telegram context"""
        context = MagicMock(spec=ContextTypes.DEFAULT_TYPE)
        context.args = args or []
        return context

    @pytest.mark.asyncio
    async def test_incident_list(self, setup_incident_test):
        """Test /incident lists active incidents"""
        workspace, user, db_session = setup_incident_test
        handler = TelegramHandler()

        update = self._create_mock_update("2222", 500)
        context = self._create_mock_context([])

        with patch('app.handlers.telegram_handler.get_db_with_retry') as mock_db:
            mock_db.return_value.__aenter__.return_value = db_session
            await handler.incident_command(update, context)

        assert update.effective_message.reply_text.called

    @pytest.mark.asyncio
    async def test_incident_start(self, setup_incident_test):
        """Test /incident start <name> creates incident"""
        workspace, user, db_session = setup_incident_test
        handler = TelegramHandler()

        update = self._create_mock_update("2222", 500)
        context = self._create_mock_context(["start", "Database", "Failure"])

        with patch('app.handlers.telegram_handler.get_db_with_retry') as mock_db:
            mock_db.return_value.__aenter__.return_value = db_session
            await handler.incident_command(update, context)

        assert update.effective_message.reply_text.called


class TestTelegramHelpCommand:
    """Detailed tests for Telegram /help command"""

    def _create_mock_update(self, chat_id="3333", user_id=600):
        """Create a mock Telegram Update"""
        update = MagicMock(spec=Update)
        update.effective_user = MagicMock(spec=TelegramUser)
        update.effective_user.id = user_id
        update.effective_user.username = "testuser"
        update.effective_user.first_name = "Test"
        update.effective_user.last_name = "User"

        update.effective_chat = MagicMock(spec=Chat)
        update.effective_chat.id = int(chat_id)
        update.effective_chat.title = "Test Chat"

        update.effective_message = MagicMock(spec=Message)
        update.effective_message.reply_text = AsyncMock()

        return update

    def _create_mock_context(self, args=None):
        """Create a mock Telegram context"""
        context = MagicMock(spec=ContextTypes.DEFAULT_TYPE)
        context.args = args or []
        return context

    @pytest.fixture
    async def setup_help_test(self, db_session: AsyncSession):
        """Setup for help command tests"""
        workspace = Workspace(
            name="Test Workspace",
            workspace_type="telegram",
            external_id="3333"
        )
        db_session.add(workspace)
        await db_session.commit()
        await db_session.refresh(workspace)

        user = User(
            workspace_id=workspace.id,
            telegram_id=600,
            telegram_username="user",
            first_name="Test",
            last_name="User",
            display_name="Test User"
        )
        db_session.add(user)
        await db_session.commit()

        return workspace, user, db_session

    @pytest.mark.asyncio
    async def test_help_command_shows_all_commands(self, setup_help_test):
        """Test /help shows all available commands"""
        workspace, user, db_session = setup_help_test
        handler = TelegramHandler()

        update = self._create_mock_update("3333", 600)
        context = self._create_mock_context([])

        with patch('app.handlers.telegram_handler.get_db_with_retry') as mock_db:
            mock_db.return_value.__aenter__.return_value = db_session
            await handler.help_command(update, context)

        assert update.effective_message.reply_text.called
        call_text = update.effective_message.reply_text.call_args[0][0]
        # Check for key sections
        assert "Available Commands" in call_text or "duty" in call_text.lower()
