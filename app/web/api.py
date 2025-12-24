"""API endpoints for web admin panel with unified service layer"""
import logging
from datetime import datetime, timedelta, date as date_type
from fastapi import APIRouter, Depends, HTTPException, Header, Body
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import AsyncSessionLocal
from app.models import User
from app.web.auth import session_manager
from app.services.user_service import UserService
from app.services.team_service import TeamService
from app.services.schedule_service import ScheduleService
from app.services.shift_service import ShiftService
from app.services.admin_service import AdminService
from app.services.stats_service import StatsService

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/admin")


async def get_db():
    """Get database session"""
    async with AsyncSessionLocal() as session:
        yield session


async def get_user_from_token(
    authorization: str = Header(None),
    db: AsyncSession = Depends(get_db)
) -> User:
    """Extract and verify user from Bearer token"""
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing or invalid authorization header")

    token = authorization.split(" ", 1)[1]
    session = session_manager.validate_session(token)

    if not session:
        raise HTTPException(status_code=401, detail="Invalid or expired token")

    # Get user from database
    user = await db.get(User, session['user_id'])
    if not user:
        raise HTTPException(status_code=401, detail="User not found")

    return user


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
    db: AsyncSession = Depends(get_db)
) -> list:
    """Get all users in workspace - uses UserService"""
    try:
        user_service = UserService(db)
        users = await user_service.get_all_users(user.workspace_id)

        return [
            {
                "id": u.id,
                "username": u.username,
                "first_name": u.first_name,
                "last_name": u.last_name or "",
                "is_admin": u.is_admin,
                "telegram_username": u.telegram_username,
            }
            for u in users
        ]
    except Exception as e:
        logger.error(f"Error getting all users: {e}")
        raise HTTPException(status_code=500, detail="Failed to get users")


# ============ Team Endpoints ============

@router.get(
    "/teams",
    tags=["Teams"],
    summary="List all teams",
    description="Получить список всех команд в workspace с информацией о членах."
)
async def get_teams(
    user: User = Depends(get_user_from_token),
    db: AsyncSession = Depends(get_db)
) -> list:
    """Get all teams in workspace - uses TeamService"""
    try:
        team_service = TeamService(db)
        teams = await team_service.get_all_teams(user.workspace_id)

        result_list = []
        for team in teams:
            result_list.append({
                "id": team.id,
                "name": team.display_name or team.name,
                "team_lead_id": team.team_lead_id,
                "members": [
                    {
                        "id": m.id,
                        "username": m.username,
                        "first_name": m.first_name,
                        "last_name": m.last_name or "",
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
    db: AsyncSession = Depends(get_db)
) -> list:
    """Get all members of a team - uses TeamService"""
    try:
        team_service = TeamService(db)
        team = await team_service.get_team(team_id, user.workspace_id)

        if not team:
            raise HTTPException(status_code=404, detail="Team not found")

        result = []
        for member in (team.members or []):
            result.append({
                "id": member.id,
                "username": member.username,
                "first_name": member.first_name,
                "last_name": member.last_name or "",
            })

        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting team members: {e}")
        raise HTTPException(status_code=500, detail="Failed to get team members")


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
    db: AsyncSession = Depends(get_db)
) -> dict:
    """Get schedule for a month - uses ScheduleService"""
    try:
        from datetime import datetime as dt

        schedule_service = ScheduleService(db)
        team_service = TeamService(db)

        # Get all schedules for the month
        start_date = dt(year, month, 1).date()
        if month == 12:
            end_date = dt(year + 1, 1, 1).date()
        else:
            end_date = dt(year, month + 1, 1).date()

        teams = await team_service.get_all_teams(user.workspace_id)

        schedule_by_date = {}
        for team in teams:
            duties = await schedule_service.get_duties_by_date_range(team, start_date, end_date - timedelta(days=1))
            for duty in duties:
                date_key = duty.date.isoformat()
                if date_key not in schedule_by_date:
                    schedule_by_date[date_key] = []
                if duty not in schedule_by_date[date_key]:
                    schedule_by_date[date_key].append(duty)

        # Build response days array
        days = []
        current_date = start_date
        while current_date < end_date:
            date_key = current_date.isoformat()
            duties = []

            if date_key in schedule_by_date:
                seen_users = set()
                for schedule in schedule_by_date[date_key]:
                    if schedule.user_id not in seen_users:
                        duties.append({
                            "id": schedule.id or 0,
                            "user_id": schedule.user_id,
                            "duty_date": schedule.date.isoformat(),
                            "user": {
                                "id": schedule.user.id,
                                "username": schedule.user.username,
                                "first_name": schedule.user.first_name,
                                "last_name": schedule.user.last_name or "",
                            },
                            "team": {
                                "id": schedule.team.id if schedule.team else None,
                                "name": schedule.team.display_name or schedule.team.name if schedule.team else None,
                            } if schedule.team else None,
                            "notes": schedule.notes,
                        })
                        seen_users.add(schedule.user_id)

            days.append({
                "date": date_key,
                "duties": duties,
            })
            current_date += timedelta(days=1)

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
    db: AsyncSession = Depends(get_db)
) -> dict:
    """Get schedule for a specific day - uses ScheduleService"""
    try:
        from datetime import datetime as dt

        date_obj = dt.fromisoformat(date).date()
        schedule_service = ScheduleService(db)
        team_service = TeamService(db)

        teams = await team_service.get_all_teams(user.workspace_id)

        duties = []
        seen_users = set()

        for team in teams:
            duty = await schedule_service.get_duty(team, date_obj)
            if duty and duty.user_id not in seen_users:
                duties.append({
                    "id": duty.id,
                    "user_id": duty.user_id,
                    "duty_date": duty.date.isoformat(),
                    "user": {
                        "id": duty.user.id,
                        "username": duty.user.username,
                        "first_name": duty.user.first_name,
                        "last_name": duty.user.last_name or "",
                    },
                    "team": {
                        "id": duty.team.id if duty.team else None,
                        "name": duty.team.display_name or duty.team.name if duty.team else None,
                    } if duty.team else None,
                    "notes": duty.notes,
                })
                seen_users.add(duty.user_id)

        return {
            "date": date,
            "duties": duties,
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

        schedule_service = ScheduleService(db)
        team_service = TeamService(db)
        user_service = UserService(db)

        # Verify team belongs to user's workspace
        team = await team_service.get_team(team_id, current_user.workspace_id)
        if not team:
            raise HTTPException(status_code=404, detail="Team not found")

        # Get target user
        target_user = await db.get(User, user_id)
        if not target_user or target_user.workspace_id != current_user.workspace_id:
            raise HTTPException(status_code=400, detail="User not found in workspace")

        date_obj = dt.fromisoformat(duty_date).date()

        # Use ScheduleService to set duty
        schedule = await schedule_service.set_duty(team, target_user, date_obj)

        return {
            "status": "assigned",
            "schedule_id": schedule.id,
            "date": duty_date
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
            raise HTTPException(status_code=404, detail="Schedule not found")

        # Verify schedule belongs to user's workspace
        if schedule_obj.team.workspace_id != user.workspace_id:
            raise HTTPException(status_code=403, detail="Not authorized")

        # Use ScheduleService to clear duty
        schedule_service = ScheduleService(db)
        success = await schedule_service.clear_duty(schedule_obj.team, schedule_obj.date)

        if not success:
            raise HTTPException(status_code=400, detail="Failed to clear duty")

        return {"status": "removed", "schedule_id": schedule_id}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error removing duty: {e}")
        raise HTTPException(status_code=500, detail="Failed to remove duty")


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
        from app.models import Team

        shift_service = ShiftService(db)
        team_service = TeamService(db)
        user_service = UserService(db)

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

        # Check for user conflicts
        conflict = await shift_service.check_user_shift_conflict(target_user, date_obj)
        if conflict:
            raise HTTPException(status_code=409, detail=f"User already assigned to {conflict['team_name']} on this date")

        # Add user to shift
        shift = await shift_service.add_user_to_shift(team, date_obj, target_user)

        return {
            "status": "assigned",
            "shift_id": shift.id,
            "date": shift_date,
            "user_count": len(shift.users)
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

        shift_service = ShiftService(db)
        team_service = TeamService(db)

        # Verify team belongs to user's workspace and has shifts enabled
        team = await team_service.get_team(team_id, current_user.workspace_id)
        if not team:
            raise HTTPException(status_code=404, detail="Team not found")
        if not team.has_shifts:
            raise HTTPException(status_code=400, detail="This team does not have shifts enabled")

        start_date_obj = dt.fromisoformat(start_date).date()
        end_date_obj = dt.fromisoformat(end_date).date()

        # Get all target users
        users = []
        for uid in user_ids:
            user_obj = await db.get(User, uid)
            if not user_obj or user_obj.workspace_id != current_user.workspace_id:
                raise HTTPException(status_code=400, detail=f"User {uid} not found in workspace")
            users.append(user_obj)

        # Assign users to each date in range
        current_date = start_date_obj
        assignments = []
        while current_date <= end_date_obj:
            shift = await shift_service.create_shift(team, current_date, users)
            assignments.append({
                "date": current_date.isoformat(),
                "shift_id": shift.id,
                "user_count": len(shift.users)
            })
            current_date += timedelta(days=1)

        return {
            "status": "bulk_assigned",
            "total_dates": len(assignments),
            "assignments": assignments
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error bulk assigning shifts: {e}")
        raise HTTPException(status_code=500, detail="Failed to bulk assign shifts")


@router.get(
    "/shifts/date/{shift_date}",
    tags=["Schedules"],
    summary="Get shifts for a date",
    description="Получить все смены на конкретную дату."
)
async def get_shifts_for_date(
    shift_date: str,
    team_id: int = None,
    user: User = Depends(get_user_from_token),
    db: AsyncSession = Depends(get_db)
) -> dict:
    """Get shifts for a specific date, optionally filtered by team"""
    try:
        from datetime import datetime as dt
        from app.models import Shift

        date_obj = dt.fromisoformat(shift_date).date()
        shift_service = ShiftService(db)
        team_service = TeamService(db)

        shifts = []

        if team_id:
            # Get shifts for specific team
            team = await team_service.get_team(team_id, user.workspace_id)
            if not team:
                raise HTTPException(status_code=404, detail="Team not found")

            shift = await shift_service.get_shift(team, date_obj)
            if shift:
                shifts.append({
                    "id": shift.id,
                    "date": shift.date.isoformat(),
                    "team": {
                        "id": shift.team.id,
                        "name": shift.team.display_name or shift.team.name,
                    },
                    "users": [
                        {
                            "id": u.id,
                            "username": u.username,
                            "first_name": u.first_name,
                            "last_name": u.last_name or "",
                        }
                        for u in shift.users
                    ]
                })
        else:
            # Get all shifts for this date across all teams with shifts
            teams = await team_service.get_all_teams(user.workspace_id)
            for team in teams:
                if team.has_shifts:
                    shift = await shift_service.get_shift(team, date_obj)
                    if shift:
                        shifts.append({
                            "id": shift.id,
                            "date": shift.date.isoformat(),
                            "team": {
                                "id": shift.team.id,
                                "name": shift.team.display_name or shift.team.name,
                            },
                            "users": [
                                {
                                    "id": u.id,
                                    "username": u.username,
                                    "first_name": u.first_name,
                                    "last_name": u.last_name or "",
                                }
                                for u in shift.users
                            ]
                        })

        return {
            "date": shift_date,
            "shifts": shifts
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting shifts for date: {e}")
        raise HTTPException(status_code=500, detail="Failed to get shifts")


@router.get(
    "/shifts/range",
    tags=["Schedules"],
    summary="Get shifts for date range",
    description="Получить все смены за период дат."
)
async def get_shifts_range(
    start_date: str,
    end_date: str,
    team_id: int = None,
    user: User = Depends(get_user_from_token),
    db: AsyncSession = Depends(get_db)
) -> dict:
    """Get shifts for a date range, optionally filtered by team"""
    try:
        from datetime import datetime as dt

        start_date_obj = dt.fromisoformat(start_date).date()
        end_date_obj = dt.fromisoformat(end_date).date()
        shift_service = ShiftService(db)
        team_service = TeamService(db)

        shifts_by_date = {}

        if team_id:
            # Get shifts for specific team
            team = await team_service.get_team(team_id, user.workspace_id)
            if not team:
                raise HTTPException(status_code=404, detail="Team not found")

            shifts = await shift_service.get_shifts_by_date_range(team, start_date_obj, end_date_obj)
            for shift in shifts:
                date_key = shift.date.isoformat()
                shifts_by_date[date_key] = {
                    "id": shift.id,
                    "date": shift.date.isoformat(),
                    "team": {
                        "id": shift.team.id,
                        "name": shift.team.display_name or shift.team.name,
                    },
                    "users": [
                        {
                            "id": u.id,
                            "username": u.username,
                            "first_name": u.first_name,
                            "last_name": u.last_name or "",
                        }
                        for u in shift.users
                    ]
                }
        else:
            # Get shifts for all teams with shifts enabled
            teams = await team_service.get_all_teams(user.workspace_id)
            for team in teams:
                if team.has_shifts:
                    shifts = await shift_service.get_shifts_by_date_range(team, start_date_obj, end_date_obj)
                    for shift in shifts:
                        date_key = shift.date.isoformat()
                        if date_key not in shifts_by_date:
                            shifts_by_date[date_key] = []

                        shifts_by_date[date_key].append({
                            "id": shift.id,
                            "date": shift.date.isoformat(),
                            "team": {
                                "id": shift.team.id,
                                "name": shift.team.display_name or shift.team.name,
                            },
                            "users": [
                                {
                                    "id": u.id,
                                    "username": u.username,
                                    "first_name": u.first_name,
                                    "last_name": u.last_name or "",
                                }
                                for u in shift.users
                            ]
                        })

        # Build sorted response
        dates = sorted(shifts_by_date.keys())
        return {
            "start_date": start_date,
            "end_date": end_date,
            "shifts_by_date": {date: shifts_by_date[date] for date in dates}
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting shifts range: {e}")
        raise HTTPException(status_code=500, detail="Failed to get shifts")


@router.delete(
    "/shifts/{shift_id}/members/{user_id}",
    tags=["Schedules"],
    summary="Remove user from shift",
    description="Удалить пользователя из смены."
)
async def remove_shift_member(
    shift_id: int,
    user_id: int,
    current_user: User = Depends(get_user_from_token),
    db: AsyncSession = Depends(get_db)
) -> dict:
    """Remove user from shift"""
    try:
        from app.models import Shift, Team

        shift = await db.get(Shift, shift_id)
        if not shift:
            raise HTTPException(status_code=404, detail="Shift not found")

        # Verify shift belongs to user's workspace
        if shift.team.workspace_id != current_user.workspace_id:
            raise HTTPException(status_code=403, detail="Not authorized")

        # Get the user to remove
        target_user = await db.get(User, user_id)
        if not target_user:
            raise HTTPException(status_code=404, detail="User not found")

        # Use ShiftService to remove user
        shift_service = ShiftService(db)
        team = await db.get(Team, shift.team_id)
        result = await shift_service.remove_user_from_shift(team, shift.date, target_user)

        if not result:
            raise HTTPException(status_code=400, detail="Failed to remove user from shift")

        return {
            "status": "removed",
            "shift_id": shift_id,
            "user_id": user_id,
            "remaining_users": len(result.users)
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error removing shift member: {e}")
        raise HTTPException(status_code=500, detail="Failed to remove shift member")


@router.delete(
    "/shifts/{shift_id}",
    tags=["Schedules"],
    summary="Delete entire shift",
    description="Удалить смену полностью (все люди)."
)
async def delete_shift(
    shift_id: int,
    current_user: User = Depends(get_user_from_token),
    db: AsyncSession = Depends(get_db)
) -> dict:
    """Delete entire shift"""
    try:
        from app.models import Shift, Team

        shift = await db.get(Shift, shift_id)
        if not shift:
            raise HTTPException(status_code=404, detail="Shift not found")

        # Verify shift belongs to user's workspace
        if shift.team.workspace_id != current_user.workspace_id:
            raise HTTPException(status_code=403, detail="Not authorized")

        # Use ShiftService to clear shift
        shift_service = ShiftService(db)
        team = await db.get(Team, shift.team_id)
        success = await shift_service.clear_shift(team, shift.date)

        if not success:
            raise HTTPException(status_code=400, detail="Failed to delete shift")

        return {"status": "deleted", "shift_id": shift_id}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting shift: {e}")
        raise HTTPException(status_code=500, detail="Failed to delete shift")


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
        user_service = UserService(db)
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
        admin_service = AdminService(db)
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
        admin_service = AdminService(db)
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
        admin_service = AdminService(db)
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
    db: AsyncSession = Depends(get_db)
) -> dict:
    """Get all schedules within a date range - uses ScheduleService"""
    try:
        from datetime import datetime as dt

        start = dt.fromisoformat(start_date).date()
        end = dt.fromisoformat(end_date).date()

        schedule_service = ScheduleService(db)
        team_service = TeamService(db)

        teams = await team_service.get_all_teams(user.workspace_id)

        schedules = []
        for team in teams:
            team_duties = await schedule_service.get_duties_by_date_range(team, start, end)
            for duty in team_duties:
                schedules.append({
                    "id": duty.id,
                    "user_id": duty.user_id,
                    "team_id": duty.team_id,
                    "duty_date": duty.date.isoformat(),
                    "user": {
                        "id": duty.user.id,
                        "username": duty.user.username,
                        "first_name": duty.user.first_name,
                        "last_name": duty.user.last_name or "",
                    },
                    "team": {
                        "id": duty.team.id if duty.team else None,
                        "name": duty.team.display_name or duty.team.name if duty.team else None,
                    } if duty.team else None,
                    "notes": duty.notes,
                })

        return {
            "start_date": start_date,
            "end_date": end_date,
            "total_count": len(schedules),
            "schedules": schedules
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
    db: AsyncSession = Depends(get_db)
) -> dict:
    """Get schedule statistics - uses StatsService"""
    try:
        from datetime import datetime as dt

        stats_service = StatsService(db)

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
        schedule_service = ScheduleService(db)
        team_service = TeamService(db)

        teams = await team_service.get_all_teams(user.workspace_id)
        total_duties = 0
        unique_users = set()

        for team in teams:
            duties = await schedule_service.get_duties_by_date_range(team, start, end)
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

        schedule_service = ScheduleService(db)
        team_service = TeamService(db)

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
        if not user.is_admin:
            raise HTTPException(status_code=403, detail="Only admins can assign duties")

        schedule_service = ScheduleService(db)
        team_service = TeamService(db)

        start = datetime.strptime(start_date, '%Y-%m-%d').date()
        end = datetime.strptime(end_date, '%Y-%m-%d').date()

        team = await team_service.get_team(team_id) if team_id else None

        created_count = 0
        current_date = start
        while current_date <= end:
            for user_id in user_ids:
                try:
                    await schedule_service.set_duty(team, user_id, current_date)
                    created_count += 1
                except Exception:
                    pass  # Skip if already exists
            current_date += timedelta(days=1)

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
    new_date: str = Body(..., embed=False),
    user: User = Depends(get_user_from_token),
    db: AsyncSession = Depends(get_db)
) -> dict:
    """Move duty to different date"""
    try:
        if not user.is_admin:
            raise HTTPException(status_code=403, detail="Only admins can modify duties")

        schedule_service = ScheduleService(db)
        new_date_obj = datetime.strptime(new_date, '%Y-%m-%d').date()

        # Get schedule
        from sqlalchemy import select
        stmt = select(schedule_service.schedule_model).where(schedule_service.schedule_model.id == schedule_id)
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
    user_id: int = Body(..., embed=False),
    user: User = Depends(get_user_from_token),
    db: AsyncSession = Depends(get_db)
) -> dict:
    """Replace person in duty with different user"""
    try:
        if not user.is_admin:
            raise HTTPException(status_code=403, detail="Only admins can modify duties")

        from sqlalchemy import select
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

        team_service = TeamService(db)
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

        team_service = TeamService(db)
        team = await team_service.get_team(team_id, user.workspace_id)
        if not team:
            raise HTTPException(status_code=404, detail="Team not found")

        team = await team_service.update_team(
            team=team,
            name=name,
            display_name=display_name,
            has_shifts=has_shifts
        )

        if team_lead_id is not None:
            team_lead = await db.get(User, team_lead_id)
            if team_lead:
                team = await team_service.set_team_lead(team, team_lead)

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

        team_service = TeamService(db)
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
    user_id: int = Body(..., embed=False),
    user: User = Depends(get_user_from_token),
    db: AsyncSession = Depends(get_db)
) -> dict:
    """Add member to team"""
    try:
        if not user.is_admin:
            raise HTTPException(status_code=403, detail="Only admins can manage team members")

        team_service = TeamService(db)
        team = await team_service.get_team(team_id, user.workspace_id)
        if not team:
            raise HTTPException(status_code=404, detail="Team not found")

        member = await db.get(User, user_id)
        if not member:
            raise HTTPException(status_code=404, detail="User not found")

        await team_service.add_member(team, member)

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

        team_service = TeamService(db)
        team = await team_service.get_team(team_id, user.workspace_id)
        if not team:
            raise HTTPException(status_code=404, detail="Team not found")

        member = await db.get(User, member_id)
        if not member:
            raise HTTPException(status_code=404, detail="User not found")

        await team_service.remove_member(team, member)

        return {"status": "removed"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error removing team member: {e}")
        raise HTTPException(status_code=500, detail="Failed to remove team member")


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
