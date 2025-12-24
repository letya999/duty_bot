"""Dependency injection setup for repositories and services."""

from sqlalchemy.ext.asyncio import AsyncSession
from app.database import AsyncSessionLocal
from app.repositories import (
    UserRepository,
    TeamRepository,
    WorkspaceRepository,
    ScheduleRepository,
    ShiftRepository,
    EscalationRepository,
    AdminLogRepository,
    RotationConfigRepository,
)


async def get_db() -> AsyncSession:
    """Get database session."""
    async with AsyncSessionLocal() as session:
        yield session


async def get_user_repository(db: AsyncSession) -> UserRepository:
    """Get user repository."""
    return UserRepository(db)


async def get_team_repository(db: AsyncSession) -> TeamRepository:
    """Get team repository."""
    return TeamRepository(db)


async def get_workspace_repository(db: AsyncSession) -> WorkspaceRepository:
    """Get workspace repository."""
    return WorkspaceRepository(db)


async def get_schedule_repository(db: AsyncSession) -> ScheduleRepository:
    """Get schedule repository."""
    return ScheduleRepository(db)


async def get_shift_repository(db: AsyncSession) -> ShiftRepository:
    """Get shift repository."""
    return ShiftRepository(db)


async def get_escalation_repository(db: AsyncSession) -> EscalationRepository:
    """Get escalation repository."""
    return EscalationRepository(db)


async def get_admin_log_repository(db: AsyncSession) -> AdminLogRepository:
    """Get admin log repository."""
    return AdminLogRepository(db)


async def get_rotation_config_repository(db: AsyncSession) -> RotationConfigRepository:
    """Get rotation config repository."""
    return RotationConfigRepository(db)
