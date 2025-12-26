"""API endpoints for web admin panel with unified service layer"""
import logging
from datetime import datetime, timedelta, date as date_type
from fastapi import APIRouter, Depends, HTTPException, Header, Body
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_, func, case

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
from app.models import User
from app.auth import session_manager
from app.schemas.admin import (
    UserResponse,
    TeamResponse,
    TeamDetailResponse,
    ScheduleResponse,
    ErrorResponse,
)
from app.services.user_service import UserService
from app.services.team_service import TeamService
from app.services.schedule_service import ScheduleService
from app.services.escalation_service import EscalationService
from app.services.rotation_service import RotationService
from app.services.admin_service import AdminService
from app.services.stats_service import StatsService
from app.repositories import (
    UserRepository, TeamRepository, ScheduleRepository,
    EscalationRepository, RotationConfigRepository, AdminLogRepository,
    GoogleCalendarRepository
)

from app.exceptions import (
    AuthenticationError,
    AuthorizationError,
    NotFoundError,
    ValidationError,
    ConflictError,
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/admin")


async def get_user_service(user_repo: UserRepository = Depends(get_user_repository), admin_log_repo: AdminLogRepository = Depends(get_admin_log_repository)) -> UserService:
    """Get user service with repositories"""
    return UserService(user_repo, admin_log_repo)


async def get_team_service(team_repo: TeamRepository = Depends(get_team_repository)) -> TeamService:
    """Get team service with repositories"""
    return TeamService(team_repo)


async def get_schedule_service(schedule_repo: ScheduleRepository = Depends(get_schedule_repository), google_calendar_repo: GoogleCalendarRepository = Depends(get_google_calendar_repository)) -> ScheduleService:
    """Get schedule service with repositories"""
    return ScheduleService(schedule_repo, google_calendar_repo)



async def get_escalation_service(escalation_repo: EscalationRepository = Depends(get_escalation_repository)) -> EscalationService:
    """Get escalation service with repositories"""
    return EscalationService(escalation_repo)


async def get_rotation_service(rotation_config_repo: RotationConfigRepository = Depends(get_rotation_config_repository), schedule_repo: ScheduleRepository = Depends(get_schedule_repository), user_repo: UserRepository = Depends(get_user_repository)) -> RotationService:
    """Get rotation service with repositories"""
    return RotationService(rotation_config_repo, schedule_repo, user_repo)


async def get_admin_service(admin_log_repo: AdminLogRepository = Depends(get_admin_log_repository), user_repo: UserRepository = Depends(get_user_repository)) -> AdminService:
    """Get admin service with repositories"""
    return AdminService(admin_log_repo, user_repo)


async def get_stats_service(db: AsyncSession = Depends(get_db)) -> StatsService:
    """Get stats service"""
    return StatsService(db)


from app.config import get_settings

async def get_user_from_token(
    authorization: str = Header(None),
    user_repo: UserRepository = Depends(get_user_repository)
) -> User:
    """Extract and verify user from Bearer token"""
    if not authorization or not authorization.startswith("Bearer "):
        raise AuthenticationError("Missing or invalid authorization header")

    token = authorization.split(" ", 1)[1]
    session = session_manager.validate_session(token)

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


class UserUpdateRequest(BaseModel):
    display_name: str | None = None
    first_name: str | None = None
    last_name: str | None = None

# ============ User Endpoints ============

@router.get(
    "/user/info",
    tags=["Users"],
    summary="Get current user information",
    description="Получить информацию о текущем авторизованном пользователе. Требует валидный Bearer token."
)
async def get_user_info(user: User = Depends(get_user_from_token)) -> dict:
    """Get current user info - returns authenticated user details"""
    return {
        "id": user.id,
        "username": user.username,
        "first_name": user.first_name,
        "last_name": user.last_name or "",
        "is_admin": user.is_admin,
        "workspace_id": user.workspace_id,
    }


@router.get(
    "/users",
    tags=["Users"],
    summary="List all users",
    description="Получить список всех пользователей в workspace."
)
async def get_all_users(
    user: User = Depends(get_user_from_token),
    user_service: UserService = Depends(get_user_service)
) -> list:
    """Get all users in workspace - uses UserService"""
    try:
        users = await user_service.get_all_users(user.workspace_id)

        return [
            {
                "id": u.id,
                "workspace_id": u.workspace_id,
                "telegram_id": str(u.telegram_id) if u.telegram_id else None,
                "telegram_username": u.telegram_username,
                "username": u.username,
                "slack_user_id": u.slack_user_id,
                "first_name": u.first_name,
                "last_name": u.last_name or "",
                "display_name": u.display_name,
                "is_admin": u.is_admin,
                "created_at": u.created_at.isoformat() if u.created_at else None,
            }
            for u in users
        ]
    except Exception as e:
        logger.error(f"Error getting all users: {e}")
        raise HTTPException(status_code=500, detail="Failed to get users")


@router.put(
    "/users/{user_id}",
    tags=["Users"],
    summary="Update user information",
    description="Обновить информацию о пользователе (например, display_name)."
)
async def update_user_info(
    user_id: int,
    data: UserUpdateRequest,
    user: User = Depends(get_user_from_token),
    user_service: UserService = Depends(get_user_service)
) -> dict:
    """Update user info"""
    try:
        logger.info(f"Updating user {user_id}: {data.model_dump(exclude_unset=True)}")
        if not user.is_admin:
            logger.warning(f"User {user.id} tried to update user {user_id} without admin perms")
            raise HTTPException(status_code=403, detail="Only admins can update user info")

        update_data = data.model_dump(exclude_unset=True)

        if not update_data:
            logger.warning(f"No update data provided for user {user_id}")
            raise HTTPException(status_code=400, detail="No update data provided")

        updated_user = await user_service.update_user(user_id, user.workspace_id, update_data)
        if not updated_user:
            logger.error(f"User {user_id} not found in workspace {user.workspace_id}")
            raise HTTPException(status_code=404, detail="User not found in this workspace")

        logger.info(f"Successfully updated user {user_id}: display_name={updated_user.display_name}")
        return {
            "id": updated_user.id,
            "display_name": updated_user.display_name,
            "first_name": updated_user.first_name,
            "last_name": updated_user.last_name,
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating user {user_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to update user")


# ============ Team Endpoints ============

@router.get(
    "/teams",
    tags=["Teams"],
    summary="List all teams",
    description="Получить список всех команд в workspace с информацией о членах."
)
async def get_teams(
    user: User = Depends(get_user_from_token),
    team_service: TeamService = Depends(get_team_service)
) -> list:
    """Get all teams in workspace - uses TeamService"""
    try:
        teams = await team_service.get_all_teams(user.workspace_id)

        result_list = []
        for team in teams:
            result_list.append({
                "id": team.id,
                "name": team.name,
                "display_name": team.display_name,
                "has_shifts": team.has_shifts,
                "team_lead_id": team.team_lead_id,
                "members": [
                    {
                        "id": m.id,
                        "username": m.username,
                        "telegram_username": m.telegram_username,
                        "slack_user_id": m.slack_user_id,
                        "first_name": m.first_name,
                        "last_name": m.last_name or "",
                        "display_name": m.display_name,
                    }
                    for m in (team.members or [])
                ]
            })

        return result_list
    except Exception as e:
        logger.error(f"Error getting teams: {e}")
        raise HTTPException(status_code=500, detail="Failed to get teams")


@router.get("/teams/{team_id}/members")
async def get_team_members(
    team_id: int,
    user: User = Depends(get_user_from_token),
    team_service: TeamService = Depends(get_team_service)
) -> list:
    """Get all members of a team - uses TeamService"""
    try:
        team = await team_service.get_team(team_id, user.workspace_id)

        if not team:
            raise NotFoundError("Team")

        result = []
        for member in (team.members or []):
            result.append({
                "id": member.id,
                "workspace_id": member.workspace_id,
                "telegram_id": str(member.telegram_id) if member.telegram_id else None,
                "telegram_username": member.telegram_username,
                "username": member.username,
                "slack_user_id": member.slack_user_id,
                "first_name": member.first_name,
                "last_name": member.last_name or "",
                "display_name": member.display_name,
                "is_admin": member.is_admin,
                "created_at": member.created_at.isoformat() if member.created_at else None,
            })

        return result
    except NotFoundError:
        raise
    except Exception as e:
        logger.error(f"Error getting team members: {e}")
        raise ValidationError("Failed to get team members")


# ============ Schedule Endpoints ============

@router.get(
    "/schedule/month",
    tags=["Schedules"],
    summary="Get month schedule",
    description="Получить дежурства на месяц с указанным годом и месяцем."
)
async def get_month_schedule(
    year: int,
    month: int,
    user: User = Depends(get_user_from_token),
    schedule_service: ScheduleService = Depends(get_schedule_service),
    team_service: TeamService = Depends(get_team_service),
    db: AsyncSession = Depends(get_db)
) -> dict:
    """Get schedule for a month - uses ScheduleService"""
    try:
        from app.config.api_utils import (
            get_month_dates, 
            get_schedules_for_period,
            build_schedule_by_date,
            build_days_array
        )

        start_date, end_date = await get_month_dates(year, month)
        schedules = await get_schedules_for_period(db, user, start_date, end_date)
        
        # Build schedule map using utility
        schedule_by_date = await build_schedule_by_date(schedules)
        days = await build_days_array(start_date, end_date, schedule_by_date)

        return {
            "year": year,
            "month": month,
            "days": days
        }
    except Exception as e:
        logger.error(f"Error getting month schedule: {e}")
        raise HTTPException(status_code=500, detail="Failed to get schedule")


@router.get(
    "/schedule/day/{date}",
    tags=["Schedules"],
    summary="Get daily schedule",
    description="Получить дежурства на конкретный день."
)
async def get_daily_schedule(
    date: str,
    user: User = Depends(get_user_from_token),
    schedule_service: ScheduleService = Depends(get_schedule_service),
    team_service: TeamService = Depends(get_team_service),
    db: AsyncSession = Depends(get_db)
) -> dict:
    """Get schedule for a specific day - uses ScheduleService"""
    try:
        from datetime import datetime as dt
        from app.config.api_utils import (
            get_daily_schedules,
            build_daily_users_list
        )

        date_obj = dt.fromisoformat(date).date()
        schedules = await get_daily_schedules(db, user, date_obj)
        users_result = await build_daily_users_list(schedules)
        
        return {
            "date": date,
            "users": users_result["users"],
            "count": users_result["count"]
        }
    except Exception as e:
        logger.error(f"Error getting daily schedule: {e}")
        raise HTTPException(status_code=500, detail="Failed to get schedule")


@router.post(
    "/schedule/assign",
    tags=["Schedules"],
    summary="Create or update duty assignment",
    description="Назначить пользователя на дежурство на конкретный день."
)
async def assign_duty(
    user_id: int = Body(..., embed=True),
    duty_date: str = Body(..., embed=True),
    team_id: int = Body(..., embed=True),
    current_user: User = Depends(get_user_from_token),
    db: AsyncSession = Depends(get_db)
) -> dict:
    """Assign duty to a user - uses ScheduleService"""
    try:
        from datetime import datetime as dt

        schedule_service = ScheduleService(ScheduleRepository(db))
        team_service = TeamService(TeamRepository(db))
        user_service = UserService(UserRepository(db))

        # Verify team belongs to user's workspace
        team = await team_service.get_team(team_id, current_user.workspace_id)
        if not team:
            raise HTTPException(status_code=404, detail="Team not found")

        # Get target user
        target_user = await db.get(User, user_id)
        if not target_user or target_user.workspace_id != current_user.workspace_id:
            raise HTTPException(status_code=400, detail="User not found in workspace")

        date_obj = dt.fromisoformat(duty_date).date()

        # Use ScheduleService to set duty - it now handles both shifts and regular duties
        schedule = await schedule_service.set_duty(
            team.id, 
            target_user.id, 
            date_obj, 
            is_shift=team.has_shifts
        )

        return {
            "status": "assigned",
            "schedule_id": schedule.id,
            "date": duty_date,
            "is_shift": schedule.is_shift
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error assigning duty: {e}")
        raise HTTPException(status_code=500, detail="Failed to assign duty")


@router.delete(
    "/schedule/{schedule_id}",
    tags=["Schedules"],
    summary="Delete duty assignment",
    description="Удалить дежурство по его ID."
)
async def remove_duty(
    schedule_id: int,
    user: User = Depends(get_user_from_token),
    db: AsyncSession = Depends(get_db)
) -> dict:
    """Remove duty assignment - uses ScheduleService"""
    try:
        from app.models import Schedule

        schedule_obj = await db.get(Schedule, schedule_id)
        if not schedule_obj:
            raise NotFoundError("Schedule")

        # Verify schedule belongs to user's workspace
        if schedule_obj.team.workspace_id != user.workspace_id:
            raise AuthorizationError("Not authorized to modify this schedule")

        # Use ScheduleService to clear duty
        schedule_service = ScheduleService(ScheduleRepository(db))
        success = await schedule_service.clear_duty(schedule_obj.team_id, schedule_obj.date)

        if not success:
            raise ValidationError("Failed to clear duty")

        return {"status": "removed", "schedule_id": schedule_id}
    except (NotFoundError, AuthorizationError, ValidationError):
        raise
    except Exception as e:
        logger.error(f"Error removing duty: {e}")
        raise ValidationError("Failed to remove duty")


# ============ Shift Endpoints (for teams with has_shifts=True) ============

@router.post(
    "/shifts/assign",
    tags=["Schedules"],
    summary="Assign user to shift",
    description="Добавить пользователя на смену. Используется для команд с включенными сменами (has_shifts=true)."
)
async def assign_shift(
    user_id: int = Body(..., embed=True),
    shift_date: str = Body(..., embed=True),
    team_id: int = Body(..., embed=True),
    current_user: User = Depends(get_user_from_token),
    db: AsyncSession = Depends(get_db)
) -> dict:
    """Assign user to shift - for teams with shifts enabled"""
    try:
        from datetime import datetime as dt

        schedule_service = ScheduleService(ScheduleRepository(db))
        team_service = TeamService(TeamRepository(db))

        # Verify team belongs to user's workspace and has shifts enabled
        team = await team_service.get_team(team_id, current_user.workspace_id)
        if not team:
            raise HTTPException(status_code=404, detail="Team not found")
        if not team.has_shifts:
            raise HTTPException(status_code=400, detail="This team does not have shifts enabled")

        # Get target user
        target_user = await db.get(User, user_id)
        if not target_user or target_user.workspace_id != current_user.workspace_id:
            raise HTTPException(status_code=400, detail="User not found in workspace")

        date_obj = dt.fromisoformat(shift_date).date()

        # Check for user conflicts (filtered to current workspace)
        conflict = await schedule_service.check_user_schedule_conflict(target_user.id, date_obj, current_user.workspace_id)
        if conflict:
            raise HTTPException(status_code=409, detail=f"User already assigned to {conflict['team_name']} on this date")

        # Add user to shift
        shift = await schedule_service.set_duty(team.id, target_user.id, date_obj, is_shift=True)

        return {
            "status": "assigned",
            "shift_id": shift.id,
            "date": shift_date,
            "user_id": target_user.id
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error assigning shift: {e}")
        raise HTTPException(status_code=500, detail="Failed to assign shift")


@router.post(
    "/shifts/assign-bulk",
    tags=["Schedules"],
    summary="Bulk assign users to shifts",
    description="Добавить нескольких пользователей на смены в диапазон дат. Используется для команд с включенными сменами."
)
async def assign_shifts_bulk(
    user_ids: list[int] = Body(..., embed=True),
    start_date: str = Body(..., embed=True),
    end_date: str = Body(..., embed=True),
    team_id: int = Body(..., embed=True),
    current_user: User = Depends(get_user_from_token),
    db: AsyncSession = Depends(get_db)
) -> dict:
    """Bulk assign users to shifts for date range"""
    try:
        from datetime import datetime as dt

        schedule_service = ScheduleService(ScheduleRepository(db))
        team_service = TeamService(TeamRepository(db))

        # Verify team belongs to user's workspace and has shifts enabled
        team = await team_service.get_team(team_id, current_user.workspace_id)
        if not team:
            raise HTTPException(status_code=404, detail="Team not found")
        if not team.has_shifts:
            raise HTTPException(status_code=400, detail="This team does not have shifts enabled")

        start_date_obj = dt.fromisoformat(start_date).date()
        end_date_obj = dt.fromisoformat(end_date).date()

        # Assign each user to each date in range
        current_date = start_date_obj
        assignments = []
        while current_date <= end_date_obj:
            for uid in user_ids:
                # set_duty handles is_shift and avoids duplicates if user already assigned
                schedule = await schedule_service.set_duty(
                    team.id, 
                    uid, 
                    current_date, 
                    is_shift=True, 
                    commit=False
                )
                assignments.append({
                    "date": current_date.isoformat(),
                    "schedule_id": schedule.id,
                    "user_id": uid
                })
            current_date += timedelta(days=1)

        # Final commit for all days
        await db.commit()

        return {
            "status": "bulk_assigned",
            "total_assignments": len(assignments),
            "assignments": assignments
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error bulk assigning shifts: {e}")
        raise HTTPException(status_code=500, detail="Failed to bulk assign shifts")





# ============ Admin Management ============

@router.get(
    "/admins",
    tags=["Admin"],
    summary="List all admins",
    description="Получить список всех администраторов в workspace."
)
async def get_admins(
    user: User = Depends(get_user_from_token),
    db: AsyncSession = Depends(get_db)
) -> dict:
    """Get list of all admins in workspace - uses UserService"""
    try:
        user_service = UserService(UserRepository(db))
        admins = await user_service.get_all_admins(user.workspace_id)

        return {
            "admins": [
                {
                    "id": admin.id,
                    "username": admin.username,
                    "first_name": admin.first_name,
                    "last_name": admin.last_name or "",
                    "is_admin": admin.is_admin
                }
                for admin in admins
            ]
        }
    except Exception as e:
        logger.error(f"Error getting admins: {e}")
        raise HTTPException(status_code=500, detail="Failed to get admins")


@router.post(
    "/users/{user_id}/promote",
    tags=["Admin"],
    summary="Promote user to admin",
    description="Повысить прав пользователя до администратора."
)
async def promote_user(
    user_id: int,
    current_user: User = Depends(get_user_from_token),
    db: AsyncSession = Depends(get_db)
) -> dict:
    """Promote user to admin - uses AdminService for logging"""
    try:
        if not current_user.is_admin:
            raise HTTPException(status_code=403, detail="Only admins can promote users")

        target_user = await db.get(User, user_id)
        if not target_user or target_user.workspace_id != current_user.workspace_id:
            raise HTTPException(status_code=404, detail="User not found")

        target_user.is_admin = True
        await db.commit()

        # Log action using AdminService
        admin_service = AdminService(AdminLogRepository(db))
        await admin_service.log_action(
            workspace_id=current_user.workspace_id,
            admin_id=current_user.id,
            action="promote_admin",
            target_user_id=user_id,
            details={"promoted": True}
        )

        return {
            "success": True,
            "message": f"User {target_user.username} promoted to admin",
            "user": {
                "id": target_user.id,
                "username": target_user.username,
                "first_name": target_user.first_name,
                "is_admin": target_user.is_admin
            }
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error promoting user: {e}")
        raise HTTPException(status_code=500, detail="Failed to promote user")


@router.post(
    "/users/{user_id}/demote",
    tags=["Admin"],
    summary="Demote user from admin",
    description="Удалить права администратора у пользователя."
)
async def demote_user(
    user_id: int,
    current_user: User = Depends(get_user_from_token),
    db: AsyncSession = Depends(get_db)
) -> dict:
    """Remove admin rights from user - uses AdminService for logging"""
    try:
        if not current_user.is_admin:
            raise HTTPException(status_code=403, detail="Only admins can demote users")

        target_user = await db.get(User, user_id)
        if not target_user or target_user.workspace_id != current_user.workspace_id:
            raise HTTPException(status_code=404, detail="User not found")

        if target_user.id == current_user.id:
            raise HTTPException(status_code=400, detail="Cannot demote yourself")

        target_user.is_admin = False
        await db.commit()

        # Log action using AdminService
        admin_service = AdminService(AdminLogRepository(db))
        await admin_service.log_action(
            workspace_id=current_user.workspace_id,
            admin_id=current_user.id,
            action="demote_admin",
            target_user_id=user_id,
            details={"demoted": True}
        )

        return {
            "success": True,
            "message": f"Admin rights removed from {target_user.username}",
            "user": {
                "id": target_user.id,
                "username": target_user.username,
                "first_name": target_user.first_name,
                "is_admin": target_user.is_admin
            }
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error demoting user: {e}")
        raise HTTPException(status_code=500, detail="Failed to demote user")


# ============ Admin Logs & Reports ============

@router.get(
    "/admin-logs",
    tags=["Admin"],
    summary="Get admin action logs",
    description="Получить логи всех действий администраторов."
)
async def get_admin_logs(
    limit: int = 50,
    user: User = Depends(get_user_from_token),
    db: AsyncSession = Depends(get_db)
) -> dict:
    """Get recent admin action logs - uses AdminService"""
    try:
        admin_service = AdminService(AdminLogRepository(db))
        logs = await admin_service.get_action_history(user.workspace_id, limit)

        return {
            "logs": [
                {
                    "id": log.id,
                    "admin_user_id": log.admin_user_id,
                    "action": log.action,
                    "target_user_id": log.target_user_id,
                    "timestamp": log.timestamp.isoformat(),
                    "details": log.details,
                    "admin_user": {
                        "id": log.admin_user.id,
                        "username": log.admin_user.username,
                        "first_name": log.admin_user.first_name,
                    } if log.admin_user else None,
                    "target_user": {
                        "id": log.target_user.id,
                        "username": log.target_user.username,
                        "first_name": log.target_user.first_name,
                    } if log.target_user else None,
                }
                for log in logs
            ]
        }
    except Exception as e:
        logger.error(f"Error getting admin logs: {e}")
        raise HTTPException(status_code=500, detail="Failed to get admin logs")


@router.get("/schedules/range")
async def get_schedules_by_date_range(
    start_date: str,
    end_date: str,
    user: User = Depends(get_user_from_token),
    schedule_service: ScheduleService = Depends(get_schedule_service),
    team_service: TeamService = Depends(get_team_service),
    db: AsyncSession = Depends(get_db)
) -> dict:
    """Get all schedules within a date range - uses ScheduleService"""
    try:
        from datetime import datetime as dt
        from app.config.api_utils import get_schedules_for_period

        start = dt.fromisoformat(start_date).date()
        end = dt.fromisoformat(end_date).date()

        db_schedules = await get_schedules_for_period(db, user, start, end)
        schedules_list = []

        for duty in db_schedules:
            schedules_list.append({
                "id": duty.id,
                "user_id": duty.user_id,
                "team_id": duty.team_id,
                "duty_date": duty.date.isoformat(),
                "user": {
                    "id": duty.user.id,
                    "username": duty.user.username,
                    "first_name": duty.user.first_name,
                    "last_name": duty.user.last_name or "",
                    "display_name": duty.user.display_name,
                },
                "team": {
                    "id": duty.team.id if duty.team else None,
                    "name": duty.team.name if duty.team else None,
                    "display_name": duty.team.display_name if duty.team else None,
                } if duty.team else None,
                "notes": "Shift" if duty.is_shift else None,
            })

        return {
            "start_date": start_date,
            "end_date": end_date,
            "total_count": len(schedules_list),
            "schedules": schedules_list
        }
    except Exception as e:
        logger.error(f"Error getting schedules by date range: {e}")
        raise HTTPException(status_code=500, detail="Failed to get schedules")


@router.get(
    "/stats/schedules",
    tags=["Statistics"],
    summary="Get schedule statistics",
    description="Получить статистику по дежурствам за период (по умолчанию последние 30 дней)."
)
async def get_schedule_statistics(
    start_date: str = None,
    end_date: str = None,
    user: User = Depends(get_user_from_token),
    stats_service: StatsService = Depends(get_stats_service),
    schedule_service: ScheduleService = Depends(get_schedule_service),
    team_service: TeamService = Depends(get_team_service)
) -> dict:
    """Get schedule statistics - uses StatsService"""
    try:
        from datetime import datetime as dt


        # Default to last 30 days if not specified
        if not end_date:
            end_date = dt.now().date().isoformat()
        if not start_date:
            start = dt.fromisoformat(end_date).date() - timedelta(days=30)
            start_date = start.isoformat()

        start = dt.fromisoformat(start_date).date()
        end = dt.fromisoformat(end_date).date()

        year, month = end.year, end.month

        # Use StatsService for consistent statistics calculation
        top_users_data = await stats_service.get_top_users_by_duties(user.workspace_id, year, month)

        # Get total duties for the period

        teams = await team_service.get_all_teams(user.workspace_id)
        total_duties = 0
        unique_users = set()

        for team in teams:
            duties = await schedule_service.get_duties_by_date_range(team.id, start, end)
            total_duties += len(duties)
            for duty in duties:
                unique_users.add(duty.user_id)

        return {
            "start_date": start_date,
            "end_date": end_date,
            "total_duties": total_duties,
            "total_users_with_duties": len(unique_users),
            "average_duties_per_user": round(total_duties / len(unique_users), 2) if unique_users else 0,
            "top_users": [
                {
                    "user_id": u["user_id"],
                    "username": u.get("display_name", "Unknown"),
                    "count": u.get("total_duties", 0)
                }
                for u in top_users_data[:10]
            ],
        }
    except Exception as e:
        logger.error(f"Error getting schedule statistics: {e}")
        raise HTTPException(status_code=500, detail="Failed to get statistics")


# ============ Enhanced Schedule Endpoints ============

@router.put(
    "/schedule/{schedule_id}",
    tags=["Schedules"],
    summary="Update duty assignment",
    description="Обновить существующее дежурство (пользователя, дату или команду)."
)
async def update_duty(
    schedule_id: int,
    user_id: int = Body(..., embed=False),
    duty_date: str = Body(..., embed=False),
    team_id: int | None = Body(None, embed=False),
    user: User = Depends(get_user_from_token),
    db: AsyncSession = Depends(get_db)
) -> dict:
    """Update existing duty assignment"""
    try:
        if not user.is_admin:
            raise HTTPException(status_code=403, detail="Only admins can update duties")

        schedule_service = ScheduleService(ScheduleRepository(db))
        team_service = TeamService(TeamRepository(db))

        # Get team
        team = await team_service.get_team(team_id) if team_id else None

        # Update duty
        schedule = await schedule_service.update_duty(schedule_id, user_id, duty_date, team)

        return {
            "id": schedule.id,
            "user_id": schedule.user_id,
            "duty_date": schedule.date.isoformat() if hasattr(schedule.date, 'isoformat') else str(schedule.date),
            "team_id": schedule.team_id,
        }
    except Exception as e:
        logger.error(f"Error updating duty: {e}")
        raise HTTPException(status_code=500, detail="Failed to update duty")


@router.post(
    "/schedule/assign-bulk",
    tags=["Schedules"],
    summary="Bulk assign duties",
    description="Массово назначить нескольких пользователей на диапазон дат."
)
async def assign_bulk_duties(
    user_ids: list[int] = Body(..., embed=False),
    start_date: str = Body(..., embed=False),
    end_date: str = Body(..., embed=False),
    team_id: int | None = Body(None, embed=False),
    user: User = Depends(get_user_from_token),
    db: AsyncSession = Depends(get_db)
) -> dict:
    """Assign multiple users to dates in range"""
    try:
        logger.info(f"🔵 Bulk assign started: users={user_ids}, range={start_date} to {end_date}, team={team_id}")
        if not user.is_admin:
            logger.warning(f"❌ User {user.id} tried to bulk assign without admin perms")
            raise HTTPException(status_code=403, detail="Only admins can assign duties")

        schedule_service = ScheduleService(ScheduleRepository(db))
        team_service = TeamService(TeamRepository(db))

        start = datetime.strptime(start_date, '%Y-%m-%d').date()
        end = datetime.strptime(end_date, '%Y-%m-%d').date()

        team = await team_service.get_team(team_id, user.workspace_id) if team_id else None

        if not team:
            logger.error(f"❌ Team {team_id} not found or access denied")
            raise HTTPException(status_code=400, detail="Team is required for bulk assignment")

        created_count = 0
        current_date = start
        while current_date <= end:
            for user_id in user_ids:
                try:
                    logger.debug(f"📅 Setting duty for user {user_id} on {current_date} (is_shift={team.has_shifts})")
                    await schedule_service.set_duty(
                        team.id, 
                        user_id, 
                        current_date, 
                        is_shift=team.has_shifts, 
                        commit=False
                    )
                    created_count += 1
                except Exception as e:
                    logger.warning(f"❌ Failed to set duty for user {user_id} on {current_date}: {e}")
            current_date += timedelta(days=1)

        # Final commit after all days processed
        logger.info(f"💾 Committing {created_count} assignments to database")
        await db.commit()
        logger.info(f"✅ Bulk assign completed successfully")

        return {"created": created_count, "total_expected": len(user_ids) * ((end - start).days + 1)}
    except Exception as e:
        logger.error(f"Error assigning bulk duties: {e}")
        raise HTTPException(status_code=500, detail="Failed to assign bulk duties")


@router.patch(
    "/schedule/{schedule_id}/move",
    tags=["Schedules"],
    summary="Move duty to another date",
    description="Перенести дежурство на другую дату."
)
async def move_duty(
    schedule_id: int,
    new_date: str = Body(..., embed=True),
    user: User = Depends(get_user_from_token),
    db: AsyncSession = Depends(get_db)
) -> dict:
    """Move duty to different date"""
    try:
        if not user.is_admin:
            raise HTTPException(status_code=403, detail="Only admins can modify duties")

        schedule_service = ScheduleService(ScheduleRepository(db))
        new_date_obj = datetime.strptime(new_date, '%Y-%m-%d').date()

        # Get schedule
        from sqlalchemy import select
        from app.models import Schedule
        stmt = select(Schedule).where(Schedule.id == schedule_id)
        result = await db.execute(stmt)
        schedule = result.scalar_one_or_none()

        if not schedule:
            raise HTTPException(status_code=404, detail="Schedule not found")

        # Move to new date
        schedule.date = new_date_obj
        await db.commit()

        return {"status": "moved", "new_date": new_date}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error moving duty: {e}")
        raise HTTPException(status_code=500, detail="Failed to move duty")


@router.patch(
    "/schedule/{schedule_id}/replace",
    tags=["Schedules"],
    summary="Replace duty person",
    description="Заменить человека на дежурстве на другого пользователя."
)
async def replace_duty_user(
    schedule_id: int,
    user_id: int = Body(..., embed=True),
    user: User = Depends(get_user_from_token),
    db: AsyncSession = Depends(get_db)
) -> dict:
    """Replace person in duty with different user"""
    try:
        if not user.is_admin:
            raise HTTPException(status_code=403, detail="Only admins can modify duties")

        from sqlalchemy import select, and_, or_, func, case
        from sqlalchemy.orm import selectinload, joinedload
        from app.models import Schedule as ScheduleModel

        stmt = select(ScheduleModel).where(ScheduleModel.id == schedule_id)
        result = await db.execute(stmt)
        schedule = result.scalar_one_or_none()

        if not schedule:
            raise HTTPException(status_code=404, detail="Schedule not found")

        schedule.user_id = user_id
        await db.commit()

        return {"status": "replaced", "user_id": user_id}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error replacing duty user: {e}")
        raise HTTPException(status_code=500, detail="Failed to replace duty user")


# ============ Teams Management Endpoints ============

@router.post(
    "/teams",
    tags=["Teams"],
    summary="Create new team",
    description="Создать новую команду в workspace."
)
async def create_team(
    name: str = Body(..., embed=False),
    display_name: str = Body(..., embed=False),
    has_shifts: bool = Body(False, embed=False),
    team_lead_id: int | None = Body(None, embed=False),
    user: User = Depends(get_user_from_token),
    db: AsyncSession = Depends(get_db)
) -> dict:
    """Create new team"""
    try:
        if not user.is_admin:
            raise HTTPException(status_code=403, detail="Only admins can create teams")

        team_service = TeamService(TeamRepository(db))
        team = await team_service.create_team(
            workspace_id=user.workspace_id,
            name=name,
            display_name=display_name,
            has_shifts=has_shifts,
            team_lead_id=team_lead_id
        )

        return {
            "id": team.id,
            "name": team.name,
            "display_name": team.display_name,
            "has_shifts": team.has_shifts
        }
    except Exception as e:
        logger.error(f"Error creating team: {e}")
        raise HTTPException(status_code=500, detail="Failed to create team")


@router.put(
    "/teams/{team_id}",
    tags=["Teams"],
    summary="Update team",
    description="Обновить информацию о команде (название, описание, настройки)."
)
async def update_team(
    team_id: int,
    name: str | None = Body(None, embed=False),
    display_name: str | None = Body(None, embed=False),
    has_shifts: bool | None = Body(None, embed=False),
    team_lead_id: int | None = Body(None, embed=False),
    user: User = Depends(get_user_from_token),
    db: AsyncSession = Depends(get_db)
) -> dict:
    """Update team"""
    try:
        if not user.is_admin:
            raise HTTPException(status_code=403, detail="Only admins can update teams")

        team_service = TeamService(TeamRepository(db))
        team = await team_service.get_team(team_id, user.workspace_id)
        if not team:
            raise HTTPException(status_code=404, detail="Team not found")

        team = await team_service.update_team(
            team_id=team.id,
            name=name,
            display_name=display_name,
            has_shifts=has_shifts
        )

        if team_lead_id is not None:
            team_lead = await db.get(User, team_lead_id)
            if team_lead:
                team = await team_service.set_team_lead(team.id, team_lead.id)

        return {
            "id": team.id,
            "name": team.name,
            "display_name": team.display_name,
            "has_shifts": team.has_shifts
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating team: {e}")
        raise HTTPException(status_code=500, detail="Failed to update team")


@router.delete(
    "/teams/{team_id}",
    tags=["Teams"],
    summary="Delete team",
    description="Удалить команду из workspace."
)
async def delete_team(
    team_id: int,
    user: User = Depends(get_user_from_token),
    db: AsyncSession = Depends(get_db)
) -> dict:
    """Delete team"""
    try:
        if not user.is_admin:
            raise HTTPException(status_code=403, detail="Only admins can delete teams")

        team_service = TeamService(TeamRepository(db))
        team = await team_service.get_team(team_id, user.workspace_id)
        if not team:
            raise HTTPException(status_code=404, detail="Team not found")

        await team_service.delete_team(team)

        return {"status": "deleted"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting team: {e}")
        raise HTTPException(status_code=500, detail="Failed to delete team")


@router.post(
    "/teams/{team_id}/members",
    tags=["Teams"],
    summary="Add team member",
    description="Добавить пользователя в команду."
)
async def add_team_member(
    team_id: int,
    user_id: int = Body(..., embed=True),
    user: User = Depends(get_user_from_token),
    db: AsyncSession = Depends(get_db)
) -> dict:
    """Add member to team"""
    try:
        if not user.is_admin:
            raise HTTPException(status_code=403, detail="Only admins can manage team members")

        team_service = TeamService(TeamRepository(db))
        team = await team_service.get_team(team_id, user.workspace_id)
        if not team:
            raise HTTPException(status_code=404, detail="Team not found")

        member = await db.get(User, user_id)
        if not member or member.workspace_id != user.workspace_id:
            raise HTTPException(status_code=404, detail="User not found")

        await team_service.add_member(team.id, member)

        return {"status": "added"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error adding team member: {e}")
        raise HTTPException(status_code=500, detail="Failed to add team member")


@router.delete(
    "/teams/{team_id}/members/{member_id}",
    tags=["Teams"],
    summary="Remove team member",
    description="Удалить пользователя из команды."
)
async def remove_team_member(
    team_id: int,
    member_id: int,
    user: User = Depends(get_user_from_token),
    db: AsyncSession = Depends(get_db)
) -> dict:
    """Remove member from team"""
    try:
        if not user.is_admin:
            raise HTTPException(status_code=403, detail="Only admins can manage team members")

        team_service = TeamService(TeamRepository(db))
        team = await team_service.get_team(team_id, user.workspace_id)
        if not team:
            raise HTTPException(status_code=404, detail="Team not found")

        member = await db.get(User, member_id)
        if not member or member.workspace_id != user.workspace_id:
            raise HTTPException(status_code=404, detail="User not found")

        await team_service.remove_member(team.id, member)

        return {"status": "removed"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error removing team member: {e}")
        raise HTTPException(status_code=500, detail="Failed to remove team member")


# ============ Members Management Endpoints ============

@router.post(
    "/teams/{team_id}/members/import",
    tags=["Teams"],
    summary="Import member by handle",
    description="Добавить участника по Telegram/Slack нику или ссылке."
)
async def import_team_member(
    team_id: int,
    handle: str = Body(..., embed=True),
    user: User = Depends(get_user_from_token),
    db: AsyncSession = Depends(get_db)
) -> dict:
    """Import member by handle"""
    try:
        from telegram import Bot
        from telegram.error import TelegramError
        from slack_sdk.web.async_client import AsyncWebClient
        from slack_sdk.errors import SlackApiError
        from app.config import get_settings
        
        settings = get_settings()

        if not user.is_admin:
            raise HTTPException(status_code=403, detail="Only admins can manage team members")

        team_service = TeamService(TeamRepository(db))
        team = await team_service.get_team(team_id, user.workspace_id)
        if not team:
            raise HTTPException(status_code=404, detail="Team not found")

        # Clean handle
        handle_orig = handle.strip()
        clean_handle = handle_orig
        source = "internal"
        
        # Initial info based on handle
        imported_info = {
            "first_name": clean_handle,
            "last_name": None,
            "username": clean_handle,
            "display_name": clean_handle,
            "telegram_id": None,
            "slack_id": None
        }

        # Telegram detection
        if clean_handle.startswith("https://t.me/") or clean_handle.startswith("t.me/") or clean_handle.startswith("@") or source == "telegram":
            source = "telegram"
            if clean_handle.startswith("https://t.me/"):
                clean_handle = clean_handle.replace("https://t.me/", "")
            if clean_handle.startswith("t.me/"):
                clean_handle = clean_handle.replace("t.me/", "")
            if clean_handle.startswith("@"):
                clean_handle = clean_handle[1:]
            
            imported_info["username"] = clean_handle
            imported_info["first_name"] = clean_handle
            imported_info["display_name"] = clean_handle
            
            # Try to fetch from Telegram
            if settings.telegram_token:
                try:
                    bot = Bot(token=settings.telegram_token)
                    # get_chat works for @username if bot has seen user or it's a public username
                    logger.info(f"Attempting to fetch Telegram info for @{clean_handle}")
                    chat = await bot.get_chat(f"@{clean_handle}")
                    imported_info["first_name"] = chat.first_name or clean_handle
                    imported_info["last_name"] = chat.last_name
                    imported_info["username"] = chat.username or clean_handle
                    imported_info["telegram_id"] = str(chat.id)
                    # For display name, prefer real name if available
                    if chat.first_name:
                        imported_info["display_name"] = f"{chat.first_name} {chat.last_name or ''}".strip()
                    else:
                        imported_info["display_name"] = chat.username or clean_handle
                    logger.info(f"Successfully fetched Telegram info for @{clean_handle}: ID={chat.id}")
                except Exception as e:
                    logger.warning(f"Failed to fetch Telegram info for {clean_handle}: {e}")

        # Slack detection (URL or User ID)
        elif "slack.com" in clean_handle or (clean_handle.startswith("U") and len(clean_handle) > 8):
            source = "slack"
            slack_user_id = clean_handle
            
            # Extract ID from URL if present
            if "slack.com" in clean_handle and "/team/" in clean_handle:
                parts = clean_handle.split("/team/")
                if len(parts) > 1:
                    slack_user_id = parts[1].split("/")[0].split("?")[0]
            
            imported_info["slack_id"] = slack_user_id
            
            # Try to fetch from Slack
            if settings.slack_bot_token:
                try:
                    slack_client = AsyncWebClient(token=settings.slack_bot_token)
                    resp = await slack_client.users_info(user=slack_user_id)
                    if resp["ok"]:
                        slack_user = resp["user"]
                        profile = slack_user.get("profile", {})
                        imported_info["first_name"] = profile.get("first_name") or slack_user.get("real_name") or "Slack User"
                        imported_info["last_name"] = profile.get("last_name")
                        imported_info["username"] = slack_user.get("name")
                        imported_info["slack_id"] = slack_user.get("id")
                        imported_info["display_name"] = slack_user.get("real_name") or slack_user.get("name")
                except Exception as e:
                     logger.warning(f"Failed to fetch Slack info for {slack_user_id}: {e}")

        # Try to find existing user
        user_service = UserService(UserRepository(db))
        
        # Check by telegram username or slack id or internal username
        conditions = [
            (User.telegram_username == imported_info["username"]),
            (User.username == imported_info["username"])
        ]
        if imported_info["slack_id"]:
            conditions.append(User.slack_user_id == imported_info["slack_id"])
            
        stmt = select(User).where(
            (User.workspace_id == user.workspace_id) & 
            or_(*conditions)
        )
        result = await db.execute(stmt)
        target_user = result.scalars().first()

        if not target_user:
            # Create new user
            target_user = await user_service.create_user(
                workspace_id=user.workspace_id,
                username=imported_info["username"],
                telegram_username=imported_info["username"] if source == "telegram" else None,
                first_name=imported_info["first_name"],
                last_name=imported_info["last_name"],
                slack_user_id=imported_info["slack_id"],
                telegram_id=int(imported_info["telegram_id"]) if imported_info["telegram_id"] else None,
                display_name=imported_info["display_name"]
            )
        else:
            # Update existing user info if it was missing
            updated = False
            if imported_info["telegram_id"] and not target_user.telegram_id:
                target_user.telegram_id = int(imported_info["telegram_id"])
                updated = True
            if imported_info["first_name"] and not target_user.first_name:
                target_user.first_name = imported_info["first_name"]
                updated = True
            if imported_info["last_name"] and not target_user.last_name:
                target_user.last_name = imported_info["last_name"]
                updated = True
            
            if updated:
                await db.commit()

        if not target_user:
             raise HTTPException(status_code=500, detail="Failed to find or create user")

        # Add to team
        await team_service.add_member(team.id, target_user)

        return {
            "status": "added",
            "user": {
                "id": target_user.id,
                "username": target_user.username,
                "first_name": target_user.first_name,
                "last_name": target_user.last_name,
                "display_name": target_user.display_name
            }
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error importing team member: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to import team member: {str(e)}")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error importing team member: {e}")
        raise HTTPException(status_code=500, detail="Failed to import team member")


@router.post(
    "/teams/members/move",
    tags=["Teams"],
    summary="Move member to another team",
    description="Переместить участника из одной команды в другую."
)
async def move_team_member(
    user_id: int = Body(..., embed=True),
    from_team_id: int = Body(..., embed=True),
    to_team_id: int = Body(..., embed=True),
    user: User = Depends(get_user_from_token),
    db: AsyncSession = Depends(get_db)
) -> dict:
    """Move member between teams"""
    try:
        if not user.is_admin:
            raise HTTPException(status_code=403, detail="Only admins can manage team members")

        team_service = TeamService(TeamRepository(db))
        
        # Verify teams
        from_team = await team_service.get_team(from_team_id, user.workspace_id)
        to_team = await team_service.get_team(to_team_id, user.workspace_id)
        
        if not from_team or not to_team:
            raise HTTPException(status_code=404, detail="Team not found")

        target_user = await db.get(User, user_id)
        if not target_user:
            raise HTTPException(status_code=404, detail="User not found")

        # Execute move
        await team_service.remove_member(from_team.id, target_user)
        await team_service.add_member(to_team.id, target_user)

        return {"status": "moved"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error moving team member: {e}")
        raise HTTPException(status_code=500, detail="Failed to move team member")


# ============ Escalations Management Endpoints ============

@router.get(
    "/escalations",
    tags=["Escalations"],
    summary="List escalations",
    description="Получить список эскалаций (назначений CTO) для всех команд или конкретной команды."
)
async def get_escalations(
    team_id: int | None = None,
    user: User = Depends(get_user_from_token),
    db: AsyncSession = Depends(get_db)
) -> list:
    """Get escalations"""
    try:
        from sqlalchemy import select
        from app.models import Escalation

        if team_id:
            stmt = select(Escalation).where(Escalation.team_id == team_id)
        else:
            stmt = select(Escalation)

        result = await db.execute(stmt)
        escalations = result.scalars().all()

        return [
            {
                "id": e.id,
                "team_id": e.team_id,
                "cto_id": e.cto_id,
                "team": {"id": e.team.id, "name": e.team.name} if e.team else None,
                "cto_user": {
                    "id": e.cto_user.id,
                    "first_name": e.cto_user.first_name,
                    "last_name": e.cto_user.last_name
                } if e.cto_user else None
            }
            for e in escalations
        ]
    except Exception as e:
        logger.error(f"Error getting escalations: {e}")
        raise HTTPException(status_code=500, detail="Failed to get escalations")


@router.post(
    "/escalations",
    tags=["Escalations"],
    summary="Create escalation",
    description="Создать новую эскалацию (назначить CTO команде или установить глобального CTO)."
)
async def create_escalation(
    team_id: int | None = Body(None, embed=False),
    cto_id: int = Body(..., embed=False),
    user: User = Depends(get_user_from_token),
    db: AsyncSession = Depends(get_db)
) -> dict:
    """Create escalation"""
    try:
        if not user.is_admin:
            raise HTTPException(status_code=403, detail="Only admins can manage escalations")

        from app.models import Escalation

        escalation = Escalation(
            team_id=team_id,
            cto_id=cto_id
        )
        db.add(escalation)
        await db.commit()

        return {
            "id": escalation.id,
            "team_id": escalation.team_id,
            "cto_id": escalation.cto_id
        }
    except Exception as e:
        logger.error(f"Error creating escalation: {e}")
        raise HTTPException(status_code=500, detail="Failed to create escalation")


@router.delete(
    "/escalations/{escalation_id}",
    tags=["Escalations"],
    summary="Delete escalation",
    description="Удалить эскалацию (отменить назначение CTO)."
)
async def delete_escalation(
    escalation_id: int,
    user: User = Depends(get_user_from_token),
    db: AsyncSession = Depends(get_db)
) -> dict:
    """Delete escalation"""
    try:
        if not user.is_admin:
            raise HTTPException(status_code=403, detail="Only admins can manage escalations")

        from sqlalchemy import select
        from app.models import Escalation

        stmt = select(Escalation).where(Escalation.id == escalation_id)
        result = await db.execute(stmt)
        escalation = result.scalar_one_or_none()

        if not escalation:
            raise HTTPException(status_code=404, detail="Escalation not found")

        await db.delete(escalation)
        await db.commit()

        return {"status": "deleted"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting escalation: {e}")
        raise HTTPException(status_code=500, detail="Failed to delete escalation")


# Google Calendar Integration Endpoints

from pydantic import BaseModel


class ServiceAccountKeyRequest(BaseModel):
    """Request model for service account key upload."""
    service_account_key: dict


async def get_google_calendar_service(
    google_calendar_repo: GoogleCalendarRepository = Depends(get_google_calendar_repository)
) -> GoogleCalendarService:
    """Get Google Calendar service."""
    from app.services.google_calendar_service import GoogleCalendarService
    return GoogleCalendarService(google_calendar_repo)


@router.get("/settings/google-calendar/status")
async def get_google_calendar_status(
    authorization: str = Header(None),
    user_repo: UserRepository = Depends(get_user_repository),
    google_calendar_repo: GoogleCalendarRepository = Depends(get_google_calendar_repository)
) -> dict:
    """Get Google Calendar integration status."""
    try:
        user = await get_user_from_token(authorization, user_repo)

        if not user.is_admin:
            raise HTTPException(status_code=403, detail="Only admins can access this endpoint")

        integration = await google_calendar_repo.get_by_workspace(user.workspace_id)

        if not integration:
            return {
                "is_connected": False,
                "status": "not_configured",
                "workspace_id": user.workspace_id
            }

        return {
            "is_connected": True,
            "is_active": integration.is_active,
            "public_calendar_url": integration.public_calendar_url,
            "service_account_email": integration.service_account_email,
            "last_sync_at": integration.last_sync_at.isoformat() if integration.last_sync_at else None,
            "google_calendar_id": integration.google_calendar_id,
            "workspace_id": user.workspace_id
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting Google Calendar status: {e}")
        raise HTTPException(status_code=500, detail="Failed to get Google Calendar status")


@router.post("/settings/google-calendar/setup")
async def setup_google_calendar(
    request: ServiceAccountKeyRequest,
    authorization: str = Header(None),
    user_repo: UserRepository = Depends(get_user_repository),
    google_calendar_repo: GoogleCalendarRepository = Depends(get_google_calendar_repository)
) -> dict:
    """Setup Google Calendar integration."""
    try:
        user = await get_user_from_token(authorization, user_repo)

        if not user.is_admin:
            raise HTTPException(status_code=403, detail="Only admins can access this endpoint")

        # Check if already configured
        existing = await google_calendar_repo.get_by_workspace(user.workspace_id)
        if existing:
            await google_calendar_repo.delete(existing.id)

        from app.services.google_calendar_service import GoogleCalendarService
        google_service = GoogleCalendarService(google_calendar_repo)

        integration = await google_service.setup_google_calendar(
            user.workspace_id,
            request.service_account_key
        )

        return {
            "status": "success",
            "public_calendar_url": integration.public_calendar_url,
            "google_calendar_id": integration.google_calendar_id,
            "service_account_email": integration.service_account_email
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error setting up Google Calendar: {e}")
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/settings/google-calendar")
async def disconnect_google_calendar(
    authorization: str = Header(None),
    user_repo: UserRepository = Depends(get_user_repository),
    google_calendar_repo: GoogleCalendarRepository = Depends(get_google_calendar_repository)
) -> dict:
    """Disconnect Google Calendar integration."""
    try:
        user = await get_user_from_token(authorization, user_repo)

        if not user.is_admin:
            raise HTTPException(status_code=403, detail="Only admins can access this endpoint")

        from app.services.google_calendar_service import GoogleCalendarService
        google_service = GoogleCalendarService(google_calendar_repo)

        success = await google_service.disconnect_google_calendar(user.workspace_id)

        if not success:
            raise HTTPException(status_code=404, detail="Google Calendar integration not found")

        return {"status": "disconnected"}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error disconnecting Google Calendar: {e}")
        raise HTTPException(status_code=500, detail="Failed to disconnect Google Calendar")


@router.get("/settings/google-calendar/url")
async def get_public_calendar_url(
    authorization: str = Header(None),
    user_repo: UserRepository = Depends(get_user_repository),
    google_calendar_repo: GoogleCalendarRepository = Depends(get_google_calendar_repository)
) -> dict:
    """Get public Google Calendar URL."""
    try:
        user = await get_user_from_token(authorization, user_repo)

        integration = await google_calendar_repo.get_by_workspace(user.workspace_id)

        if not integration or not integration.is_active:
            raise HTTPException(status_code=404, detail="Google Calendar not configured")

        return {
            "url": integration.public_calendar_url,
            "calendar_id": integration.google_calendar_id
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting calendar URL: {e}")
        raise HTTPException(status_code=500, detail="Failed to get calendar URL")
