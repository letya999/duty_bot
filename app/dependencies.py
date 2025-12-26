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
)


from fastapi import Depends

async def get_db() -> AsyncSession:
    """Get database session."""
    async with AsyncSessionLocal() as session:
        yield session


async def get_user_repository(db: AsyncSession = Depends(get_db)) -> UserRepository:
    """Get user repository."""
    return UserRepository(db)


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
