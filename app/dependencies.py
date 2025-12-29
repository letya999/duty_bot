"""Dependency injection setup for repositories and services."""

from sqlalchemy.ext.asyncio import AsyncSession
from app.database import AsyncSessionLocal
from app.repositories import (
    UserRepository,
    TeamRepository,
    WorkspaceRepository,
    ScheduleRepository,
    EscalationRepository,
    AdminLogRepository,
    RotationConfigRepository,
    DutyStatsRepository,
    IncidentRepository,
    GoogleCalendarRepository,
    OrganizationRepository,
    UserAccountRepository,
)


from fastapi import Depends, Header, Request
from app.auth import session_manager
from app.models import User
from app.config import get_settings
from app.exceptions import AuthenticationError

async def get_db() -> AsyncSession:
    """Get database session."""
    async with AsyncSessionLocal() as session:
        yield session


async def get_user_repository(db: AsyncSession = Depends(get_db)) -> UserRepository:
    """Get user repository."""
    return UserRepository(db)

async def get_current_user(
    request: Request,
    authorization: str = Header(None),
    user_repo: UserRepository = Depends(get_user_repository)
) -> User:
    """Extract and verify user from Bearer token or session cookie"""
    token = None
    
    # 1. Try Authorization header
    if authorization and authorization.startswith("Bearer "):
        token = authorization.split(" ", 1)[1]
    
    # 2. Try session_token cookie
    if not token:
        token = request.cookies.get("session_token")

    if not token:
        raise AuthenticationError("Missing authentication token")

    session = await session_manager.validate_session(token)

    if not session:
        raise AuthenticationError("Invalid or expired token")

    # Get user from repository
    user = await user_repo.get_by_id(session['user_id'])
    if not user:
        raise AuthenticationError("User not found")

    # Check if user is a master admin - always grant admin status in any workspace
    settings = get_settings()
    is_master = False
    if user.telegram_id and str(user.telegram_id) in settings.get_admin_ids('telegram'):
        is_master = True
    if user.slack_user_id and user.slack_user_id in settings.get_admin_ids('slack'):
        is_master = True
    
    if is_master and not user.is_admin:
        # We can temporarily set it for this request context
        user.is_admin = True
        # Optional: update in DB for future requests
        await user_repo.update(user.id, {"is_admin": True})

    return user

async def get_team_repository(db: AsyncSession = Depends(get_db)) -> TeamRepository:
    """Get team repository."""
    return TeamRepository(db)


async def get_workspace_repository(db: AsyncSession = Depends(get_db)) -> WorkspaceRepository:
    """Get workspace repository."""
    return WorkspaceRepository(db)


async def get_schedule_repository(db: AsyncSession = Depends(get_db)) -> ScheduleRepository:
    """Get schedule repository."""
    return ScheduleRepository(db)



async def get_escalation_repository(db: AsyncSession = Depends(get_db)) -> EscalationRepository:
    """Get escalation repository."""
    return EscalationRepository(db)


async def get_admin_log_repository(db: AsyncSession = Depends(get_db)) -> AdminLogRepository:
    """Get admin log repository."""
    return AdminLogRepository(db)


async def get_rotation_config_repository(db: AsyncSession = Depends(get_db)) -> RotationConfigRepository:
    """Get rotation config repository."""
    return RotationConfigRepository(db)


async def get_duty_stats_repository(db: AsyncSession = Depends(get_db)) -> DutyStatsRepository:
    """Get duty stats repository."""
    return DutyStatsRepository(db)


async def get_incident_repository(db: AsyncSession = Depends(get_db)) -> IncidentRepository:
    """Get incident repository."""
    return IncidentRepository(db)


async def get_google_calendar_repository(db: AsyncSession = Depends(get_db)) -> GoogleCalendarRepository:
    """Get Google Calendar repository."""
    return GoogleCalendarRepository(db)


async def get_organization_repository(db: AsyncSession = Depends(get_db)) -> OrganizationRepository:
    """Get organization repository."""
    return OrganizationRepository(db)


async def get_user_account_repository(db: AsyncSession = Depends(get_db)) -> UserAccountRepository:
    """Get user account repository."""
    return UserAccountRepository(db)
