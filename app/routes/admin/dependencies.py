"""Service dependencies for admin API endpoints"""
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import Depends

from app.dependencies import (
    get_db,
    get_user_repository,
    get_team_repository,
    get_workspace_repository,
    get_schedule_repository,
    get_escalation_repository,
    get_rotation_config_repository,
    get_admin_log_repository,
    get_duty_stats_repository,
    get_google_calendar_repository,
    get_organization_repository,
    get_user_account_repository,
)
from app.services.user_service import UserService
from app.services.team_service import TeamService
from app.services.schedule_service import ScheduleService
from app.services.escalation_service import EscalationService
from app.services.rotation_service import RotationService
from app.services.admin_service import AdminService
from app.services.stats_service import StatsService
from app.services.google_calendar_service import GoogleCalendarService
from app.services.organization_service import OrganizationService
from app.services.user_account_service import UserAccountService
from app.repositories import (
    UserRepository, TeamRepository, ScheduleRepository,
    EscalationRepository, RotationConfigRepository, AdminLogRepository,
    GoogleCalendarRepository, OrganizationRepository, UserAccountRepository,
    WorkspaceRepository
)


async def get_user_service(
    user_repo: UserRepository = Depends(get_user_repository),
    admin_log_repo: AdminLogRepository = Depends(get_admin_log_repository),
    user_account_repo: UserAccountRepository = Depends(get_user_account_repository)
) -> UserService:
    """Get user service with repositories"""
    return UserService(user_repo, admin_log_repo, user_account_repo)


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


async def get_organization_service(
    org_repo: OrganizationRepository = Depends(get_organization_repository),
    workspace_repo: WorkspaceRepository = Depends(get_workspace_repository),
    team_repo: TeamRepository = Depends(get_team_repository),
    db: AsyncSession = Depends(get_db)
) -> OrganizationService:
    """Get organization service"""
    return OrganizationService(org_repo, workspace_repo, team_repo, db)


async def get_user_account_service(
    user_account_repo: UserAccountRepository = Depends(get_user_account_repository),
    user_repo: UserRepository = Depends(get_user_repository),
    db: AsyncSession = Depends(get_db)
) -> UserAccountService:
    """Get user account service"""
    return UserAccountService(user_account_repo, user_repo, db)
