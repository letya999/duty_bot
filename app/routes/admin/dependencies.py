"""Service dependencies for admin API endpoints"""
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import Depends

from app.dependencies import (
    get_db,
    get_user_repository,
    get_team_repository,
    get_schedule_repository,
    get_escalation_repository,
    get_rotation_config_repository,
    get_admin_log_repository,
    get_duty_stats_repository,
    get_google_calendar_repository,
)
from app.services.user_service import UserService
from app.services.team_service import TeamService
from app.services.schedule_service import ScheduleService
from app.services.escalation_service import EscalationService
from app.services.rotation_service import RotationService
from app.services.admin_service import AdminService
from app.services.stats_service import StatsService
from app.services.google_calendar_service import GoogleCalendarService
from app.repositories import (
    UserRepository, TeamRepository, ScheduleRepository,
    EscalationRepository, RotationConfigRepository, AdminLogRepository,
    GoogleCalendarRepository
)


async def get_user_service(
    user_repo: UserRepository = Depends(get_user_repository),
    admin_log_repo: AdminLogRepository = Depends(get_admin_log_repository)
) -> UserService:
    """Get user service with repositories"""
    return UserService(user_repo, admin_log_repo)


async def get_team_service(
    team_repo: TeamRepository = Depends(get_team_repository)
) -> TeamService:
    """Get team service with repositories"""
    return TeamService(team_repo)


async def get_schedule_service(
    schedule_repo: ScheduleRepository = Depends(get_schedule_repository),
    google_calendar_repo: GoogleCalendarRepository = Depends(get_google_calendar_repository)
) -> ScheduleService:
    """Get schedule service with repositories"""
    return ScheduleService(schedule_repo, google_calendar_repo)


async def get_escalation_service(
    escalation_repo: EscalationRepository = Depends(get_escalation_repository)
) -> EscalationService:
    """Get escalation service with repositories"""
    return EscalationService(escalation_repo)


async def get_rotation_service(
    rotation_config_repo: RotationConfigRepository = Depends(get_rotation_config_repository),
    schedule_repo: ScheduleRepository = Depends(get_schedule_repository),
    user_repo: UserRepository = Depends(get_user_repository)
) -> RotationService:
    """Get rotation service with repositories"""
    return RotationService(rotation_config_repo, schedule_repo, user_repo)


async def get_admin_service(
    admin_log_repo: AdminLogRepository = Depends(get_admin_log_repository),
    user_repo: UserRepository = Depends(get_user_repository)
) -> AdminService:
    """Get admin service with repositories"""
    return AdminService(admin_log_repo, user_repo)


async def get_stats_service(
    db: AsyncSession = Depends(get_db)
) -> StatsService:
    """Get stats service"""
    return StatsService(db)


async def get_google_calendar_service(
    google_calendar_repo: GoogleCalendarRepository = Depends(get_google_calendar_repository)
) -> GoogleCalendarService:
    """Get Google Calendar service"""
    return GoogleCalendarService(google_calendar_repo)
