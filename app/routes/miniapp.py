"""Telegram Mini App API routes"""
import logging
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException, Header
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, func
from app.database import AsyncSessionLocal
from app.models import User, Team, Schedule, Shift, Workspace, ChatChannel, team_members, shift_members
from app.services.user_service import UserService
from app.services.team_service import TeamService
from app.services.schedule_service import ScheduleService
from app.services.shift_service import ShiftService
from app.config.api_utils import (
    format_user_response,
    get_month_dates,
    get_schedules_and_shifts_for_period,
    build_schedule_by_date,
    build_days_array,
    get_daily_schedules_and_shifts,
    build_daily_users_list
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/miniapp", tags=["miniapp"])


async def get_db():
    """Get database session"""
    async with AsyncSessionLocal() as session:
        yield session


async def get_user_from_telegram(
    init_data: str = Header(None, alias="X-Telegram-Init-Data"),
    db: AsyncSession = Depends(get_db)
) -> User:
    """Extract and verify user from Telegram init data"""
    if not init_data:
        raise HTTPException(status_code=401, detail="Missing Telegram init data")

    # TODO: Implement proper Telegram init data verification
    # For now, we'll just extract user ID from init data
    # In production, you should verify the HMAC signature

    try:
        # Parse init data (format: user=..&hash=...&auth_date=...)
        params = {}
        for param in init_data.split('&'):
            if '=' in param:
                key, value = param.split('=', 1)
                params[key] = value

        # In a real app, verify params['hash'] against TELEGRAM_BOT_TOKEN
        # For now we'll just trust it
        user_data = params.get('user')
        if not user_data:
            raise HTTPException(status_code=401, detail="Invalid user data")

        # user_data is JSON URL-encoded, parse it
        import json
        import urllib.parse
        user_dict = json.loads(urllib.parse.unquote(user_data))
        telegram_id = user_dict.get('id')

        if not telegram_id:
            raise HTTPException(status_code=401, detail="Missing telegram ID")

        # Find workspace by chat context - use telegram_id as workspace external_id
        # In Telegram, typically the chat_id is the workspace external_id
        workspace_stmt = select(Workspace).where(
            and_(
                Workspace.workspace_type == 'telegram',
                Workspace.external_id == str(telegram_id)
            )
        )
        workspace = (await db.execute(workspace_stmt)).scalars().first()

        if not workspace:
            # Create workspace for this user if it doesn't exist
            workspace = Workspace(
                name=f"Telegram User {telegram_id}",
                workspace_type='telegram',
                external_id=str(telegram_id)
            )
            db.add(workspace)
            await db.flush()

        # Find or create user in workspace
        user_stmt = select(User).where(
            and_(
                User.workspace_id == workspace.id,
                User.telegram_username == str(telegram_id)
            )
        )
        user = (await db.execute(user_stmt)).scalars().first()

        if not user:
            # Create user if doesn't exist
            user = User(
                workspace_id=workspace.id,
                telegram_username=str(telegram_id),
                display_name=user_dict.get('first_name', f'User {telegram_id}')
            )
            db.add(user)
            await db.flush()

        await db.commit()
        return user

    except Exception as e:
        logger.error(f"Error parsing telegram init data: {e}")
        raise HTTPException(status_code=401, detail="Invalid telegram init data")


# ============ User Endpoints ============

@router.get("/user/info")
async def get_user_info(user: User = Depends(get_user_from_telegram)) -> dict:
    """Get current user info"""
    return {
        "id": user.id,
        "telegram_id": user.telegram_username,
        "first_name": user.display_name,
        "last_name": "",
        "username": user.telegram_username
    }


# ============ Schedule Endpoints ============

@router.get("/schedule/month")
async def get_month_schedule(
    year: int,
    month: int,
    user: User = Depends(get_user_from_telegram),
    db: AsyncSession = Depends(get_db)
) -> dict:
    """Get schedule for a month"""
    try:
        # Get month dates
        start_date, end_date = await get_month_dates(year, month)

        # Get schedules and shifts
        schedules, shifts = await get_schedules_and_shifts_for_period(db, user, start_date, end_date)

        # Group by date
        schedule_by_date = await build_schedule_by_date(schedules, shifts, db)

        # Build response days array
        days = await build_days_array(start_date, end_date, schedule_by_date)

        return {
            "year": year,
            "month": month,
            "days": days
        }
    except Exception as e:
        logger.error(f"Error getting month schedule: {e}")
        raise HTTPException(status_code=500, detail="Failed to get schedule")


@router.get("/schedule/day/{date}")
async def get_daily_schedule(
    date: str,
    user: User = Depends(get_user_from_telegram),
    db: AsyncSession = Depends(get_db)
) -> dict:
    """Get schedule for a specific day"""
    try:
        from datetime import datetime as dt
        date_obj = dt.fromisoformat(date).date()

        # Get schedules and shifts for this date
        schedules, shifts = await get_daily_schedules_and_shifts(db, user, date_obj)

        # Build users list
        result = await build_daily_users_list(schedules, shifts, db)

        return {
            "date": date,
            "users": result["users"],
            "count": result["count"]
        }
    except Exception as e:
        logger.error(f"Error getting daily schedule: {e}")
        raise HTTPException(status_code=500, detail="Failed to get schedule")


@router.post("/schedule/assign")
async def assign_duty(
    team_id: int,
    user_id: int,
    date: str,
    user: User = Depends(get_user_from_telegram),
    db: AsyncSession = Depends(get_db)
) -> dict:
    """Assign duty to a user for a specific date"""
    try:
        from datetime import datetime as dt

        # Verify team belongs to user's workspace
        team_stmt = select(Team).where(
            and_(
                Team.id == team_id,
                Team.workspace_id == user.workspace_id
            )
        )
        team = (await db.execute(team_stmt)).scalars().first()

        if not team:
            raise HTTPException(status_code=404, detail="Team not found")

        # Verify user belongs to the team
        user_in_team = select(team_members).where(
            and_(
                team_members.c.team_id == team_id,
                team_members.c.user_id == user_id
            )
        )
        result = await db.execute(user_in_team)
        if not result.scalars().first():
            raise HTTPException(status_code=400, detail="User not in team")

        date_obj = dt.fromisoformat(date).date()

        # Check if schedule already exists
        existing_stmt = select(Schedule).where(
            and_(
                Schedule.team_id == team_id,
                Schedule.user_id == user_id,
                Schedule.date == date_obj
            )
        )
        existing = (await db.execute(existing_stmt)).scalars().first()

        if existing:
            return {"status": "already_assigned", "schedule_id": existing.id}

        # Create new schedule
        schedule = Schedule(
            team_id=team_id,
            user_id=user_id,
            date=date_obj
        )
        db.add(schedule)
        await db.commit()

        return {
            "status": "assigned",
            "schedule_id": schedule.id,
            "date": date
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error assigning duty: {e}")
        await db.rollback()
        raise HTTPException(status_code=500, detail="Failed to assign duty")


@router.delete("/schedule/{schedule_id}")
async def remove_duty(
    schedule_id: int,
    user: User = Depends(get_user_from_telegram),
    db: AsyncSession = Depends(get_db)
) -> dict:
    """Remove duty assignment"""
    try:
        schedule_stmt = select(Schedule).where(Schedule.id == schedule_id)
        schedule = (await db.execute(schedule_stmt)).scalars().first()

        if not schedule:
            raise HTTPException(status_code=404, detail="Schedule not found")

        # Verify schedule belongs to user's workspace
        team_stmt = select(Team).where(Team.id == schedule.team_id)
        team = (await db.execute(team_stmt)).scalars().first()

        if not team or team.workspace_id != user.workspace_id:
            raise HTTPException(status_code=403, detail="Not authorized")

        await db.delete(schedule)
        await db.commit()

        return {"status": "removed", "schedule_id": schedule_id}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error removing duty: {e}")
        await db.rollback()
        raise HTTPException(status_code=500, detail="Failed to remove duty")


# ============ Team Endpoints ============

@router.get("/teams")
async def get_teams(
    user: User = Depends(get_user_from_telegram),
    db: AsyncSession = Depends(get_db)
) -> list:
    """Get all teams in the workspace"""
    try:
        teams_stmt = select(Team).where(Team.workspace_id == user.workspace_id)
        teams = (await db.execute(teams_stmt)).scalars().all()

        result = []
        for team in teams:
            result.append({
                "id": team.id,
                "name": team.display_name,
                "team_lead_id": team.team_lead_id,
                "workspace_id": team.workspace_id
            })

        return result
    except Exception as e:
        logger.error(f"Error getting teams: {e}")
        raise HTTPException(status_code=500, detail="Failed to get teams")


@router.get("/teams/{team_id}/members")
async def get_team_members(
    team_id: int,
    user: User = Depends(get_user_from_telegram),
    db: AsyncSession = Depends(get_db)
) -> list:
    """Get all members of a team"""
    try:
        # Verify team belongs to user's workspace
        team_stmt = select(Team).where(
            and_(
                Team.id == team_id,
                Team.workspace_id == user.workspace_id
            )
        )
        team = (await db.execute(team_stmt)).scalars().first()

        if not team:
            raise HTTPException(status_code=404, detail="Team not found")

        # Get team members
        await db.refresh(team, ['members'])

        result = []
        for member in team.members:
            result.append({
                "id": member.id,
                "telegram_id": member.telegram_username,
                "first_name": member.display_name,
                "last_name": "",
                "username": member.telegram_username
            })

        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting team members: {e}")
        raise HTTPException(status_code=500, detail="Failed to get team members")


@router.get("/admins")
async def get_admins(
    user: User = Depends(get_user_from_telegram),
    db: AsyncSession = Depends(get_db)
):
    """Get list of all admins in workspace"""
    try:
        if not user.workspace_id:
            raise HTTPException(status_code=400, detail="User not assigned to workspace")

        # Get all admin users
        stmt = select(User).where(
            (User.workspace_id == user.workspace_id) &
            (User.is_admin == True)
        )
        result = await db.execute(stmt)
        admins = result.scalars().all()

        return {
            "success": True,
            "admins": [
                {
                    "id": admin.id,
                    "username": admin.username,
                    "first_name": admin.first_name,
                    "last_name": admin.last_name,
                    "is_admin": admin.is_admin
                }
                for admin in admins
            ]
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting admins: {e}")
        raise HTTPException(status_code=500, detail="Failed to get admins")


@router.post("/users/{user_id}/promote")
async def promote_user(
    user_id: int,
    current_user: User = Depends(get_user_from_telegram),
    db: AsyncSession = Depends(get_db)
):
    """Promote user to admin (admin only)"""
    try:
        # Check if current user is admin
        if not current_user.is_admin:
            raise HTTPException(status_code=403, detail="Only admins can promote users")

        # Get target user
        user = await db.get(User, user_id)
        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        # Check same workspace
        if user.workspace_id != current_user.workspace_id:
            raise HTTPException(status_code=403, detail="Cannot manage users from other workspaces")

        # Promote user
        user.is_admin = True
        await db.commit()

        # Log action
        from app.services.admin_service import AdminService
        admin_service = AdminService(db)
        await admin_service.log_action(
            workspace_id=current_user.workspace_id,
            admin_user_id=current_user.id,
            action="promote_admin",
            target_user_id=user_id,
            details={"promoted": True}
        )

        return {
            "success": True,
            "message": f"User {user.username} promoted to admin",
            "user": {
                "id": user.id,
                "username": user.username,
                "first_name": user.first_name,
                "is_admin": user.is_admin
            }
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error promoting user: {e}")
        raise HTTPException(status_code=500, detail="Failed to promote user")


@router.post("/users/{user_id}/demote")
async def demote_user(
    user_id: int,
    current_user: User = Depends(get_user_from_telegram),
    db: AsyncSession = Depends(get_db)
):
    """Remove admin rights from user (admin only)"""
    try:
        # Check if current user is admin
        if not current_user.is_admin:
            raise HTTPException(status_code=403, detail="Only admins can demote users")

        # Get target user
        user = await db.get(User, user_id)
        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        # Check same workspace
        if user.workspace_id != current_user.workspace_id:
            raise HTTPException(status_code=403, detail="Cannot manage users from other workspaces")

        # Prevent demoting yourself
        if user.id == current_user.id:
            raise HTTPException(status_code=400, detail="Cannot demote yourself")

        # Demote user
        user.is_admin = False
        await db.commit()

        # Log action
        from app.services.admin_service import AdminService
        admin_service = AdminService(db)
        await admin_service.log_action(
            workspace_id=current_user.workspace_id,
            admin_user_id=current_user.id,
            action="demote_admin",
            target_user_id=user_id,
            details={"demoted": True}
        )

        return {
            "success": True,
            "message": f"Admin rights removed from {user.username}",
            "user": {
                "id": user.id,
                "username": user.username,
                "first_name": user.first_name,
                "is_admin": user.is_admin
            }
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error demoting user: {e}")
        raise HTTPException(status_code=500, detail="Failed to demote user")
