import pytest
import asyncio
import os
from pathlib import Path
from typing import AsyncGenerator
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import declarative_base

# Load .env.test before importing app modules
def load_env_test():
    """Load environment variables from .env.test"""
    env_path = Path(__file__).parent.parent / ".env.test"
    if env_path.exists():
        with open(env_path) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    key, value = line.split("=", 1)
                    if key not in os.environ:
                        os.environ[key] = value

load_env_test()

# Import models and base
from app.models import (
    Base, Workspace, ChatChannel, User, Team, RotationConfig, Schedule,
    Escalation, EscalationEvent, AdminLog, DutyStats, Incident,
    GoogleCalendarIntegration, team_members
)
from app.database import AsyncSessionLocal


# Override database settings for tests
@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
async def test_engine():
    """Create a test database engine using in-memory SQLite"""
    # Using SQLite for simplicity in testing
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        echo=False,
        future=True,
        connect_args={"timeout": 30}
    )

    # Create all tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    yield engine

    # Clean up
    await engine.dispose()


@pytest.fixture
async def db_session(test_engine) -> AsyncGenerator[AsyncSession, None]:
    """Create a test database session"""
    async_session = async_sessionmaker(
        test_engine,
        class_=AsyncSession,
        expire_on_commit=False
    )

    async with async_session() as session:
        yield session
        await session.rollback()


@pytest.fixture
def workspace_factory():
    """Factory for creating workspace objects"""
    def create(
        name: str = "Test Workspace",
        workspace_type: str = "telegram",
        external_id: str = "123456789"
    ) -> Workspace:
        return Workspace(
            name=name,
            workspace_type=workspace_type,
            external_id=external_id,
            created_at=datetime.utcnow()
        )
    return create


@pytest.fixture
def user_factory():
    """Factory for creating user objects"""
    def create(
        workspace_id: int = 1,
        telegram_id: int = None,
        telegram_username: str = "testuser",
        slack_user_id: str = None,
        first_name: str = "Test",
        last_name: str = "User",
        display_name: str = "Test User",
        is_admin: bool = False
    ) -> User:
        return User(
            workspace_id=workspace_id,
            telegram_id=telegram_id,
            telegram_username=telegram_username,
            slack_user_id=slack_user_id,
            first_name=first_name,
            last_name=last_name,
            display_name=display_name,
            is_admin=is_admin,
            created_at=datetime.utcnow()
        )
    return create


@pytest.fixture
def team_factory():
    """Factory for creating team objects"""
    def create(
        workspace_id: int = 1,
        name: str = "Test Team",
        display_name: str = "Test Team Display",
        has_shifts: bool = False,
        team_lead_id: int = None
    ) -> Team:
        return Team(
            workspace_id=workspace_id,
            name=name,
            display_name=display_name,
            has_shifts=has_shifts,
            team_lead_id=team_lead_id,
            created_at=datetime.utcnow()
        )
    return create


@pytest.fixture
def schedule_factory():
    """Factory for creating schedule objects"""
    def create(
        team_id: int = 1,
        user_id: int = 1,
        date_obj=None,
        is_shift: bool = False
    ) -> Schedule:
        from datetime import date as date_type
        if date_obj is None:
            date_obj = date_type.today()

        return Schedule(
            team_id=team_id,
            user_id=user_id,
            date=date_obj,
            is_shift=is_shift,
            created_at=datetime.utcnow()
        )
    return create


@pytest.fixture
def escalation_factory():
    """Factory for creating escalation objects"""
    def create(
        team_id: int = 1,
        cto_id: int = 2
    ) -> Escalation:
        return Escalation(
            team_id=team_id,
            cto_id=cto_id,
            created_at=datetime.utcnow()
        )
    return create


@pytest.fixture
def incident_factory():
    """Factory for creating incident objects"""
    def create(
        workspace_id: int = 1,
        name: str = "Test Incident",
        status: str = "active",
        start_time: datetime = None,
        end_time: datetime = None
    ) -> Incident:
        if start_time is None:
            start_time = datetime.utcnow()

        return Incident(
            workspace_id=workspace_id,
            name=name,
            status=status,
            start_time=start_time,
            end_time=end_time,
            created_at=datetime.utcnow()
        )
    return create


@pytest.fixture
def chat_channel_factory():
    """Factory for creating chat channel objects"""
    def create(
        workspace_id: int = 1,
        messenger: str = "telegram",
        external_id: str = "123456789",
        display_name: str = "Test Channel"
    ) -> ChatChannel:
        return ChatChannel(
            workspace_id=workspace_id,
            messenger=messenger,
            external_id=external_id,
            display_name=display_name,
            created_at=datetime.utcnow()
        )
    return create


# Mock fixtures for external services
@pytest.fixture
def mock_google_calendar_service():
    """Mock Google Calendar service"""
    mock = AsyncMock()
    mock.sync_events = AsyncMock(return_value=None)
    mock.create_event = AsyncMock(return_value={"id": "test_event_id"})
    return mock


@pytest.fixture
def mock_telegram_bot():
    """Mock Telegram bot"""
    mock = MagicMock()
    mock.send_message = AsyncMock(return_value={"ok": True})
    mock.answer_callback_query = AsyncMock(return_value={"ok": True})
    return mock


@pytest.fixture
def mock_slack_client():
    """Mock Slack client"""
    mock = AsyncMock()
    mock.chat_postMessage = AsyncMock(return_value={"ok": True})
    mock.reactions_add = AsyncMock(return_value={"ok": True})
    return mock


@pytest.fixture
def mock_aiohttp_session():
    """Mock aiohttp session"""
    mock = AsyncMock()
    mock.get = AsyncMock(return_value=AsyncMock())
    mock.post = AsyncMock(return_value=AsyncMock())
    return mock


# Fixtures for logging and configuration
@pytest.fixture
def mock_logger():
    """Mock logger for testing"""
    return MagicMock()


@pytest.fixture
def test_settings():
    """Test settings fixture"""
    from app.config import Settings

    class TestSettings(Settings):
        database_url: str = "sqlite+aiosqlite:///:memory:"
        telegram_bot_token: str = "test_token"
        slack_bot_token: str = "test_token"
        slack_signing_secret: str = "test_secret"
        google_credentials_json: str = "{}"
        jwt_secret_key: str = "test_secret_key"
        encryption_key: str = "test_encryption_key"
        debug: bool = True

        class Config:
            env_file = ".env.test"

    return TestSettings()


# Mark all tests as asyncio by default
pytest_plugins = ('pytest_asyncio',)
