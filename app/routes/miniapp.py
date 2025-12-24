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
        # Get all schedules for the month in this workspace
        start_date = datetime(year, month, 1).date()
        if month == 12:
            end_date = datetime(year + 1, 1, 1).date()
        else:
            end_date = datetime(year, month + 1, 1).date()

        schedules_stmt = select(Schedule).where(
            and_(
                Schedule.date >= start_date,
                Schedule.date < end_date,
                Schedule.team.has(Team.workspace_id == user.workspace_id)
            )
        )
        schedules = (await db.execute(schedules_stmt)).scalars().all()

        # Also get shifts for the month
        shifts_stmt = select(Shift).where(
            and_(
                Shift.date >= start_date,
                Shift.date < end_date,
                Shift.team.has(Team.workspace_id == user.workspace_id)
            )
        )
        shifts = (await db.execute(shifts_stmt)).scalars().all()

        # Group schedules by date
        schedule_by_date = {}
        for schedule in schedules:
            date_key = schedule.date.isoformat()
            if date_key not in schedule_by_date:
                schedule_by_date[date_key] = []
            schedule_by_date[date_key].append(schedule)

        # Add shift users to schedule_by_date
        for shift in shifts:
            date_key = shift.date.isoformat()
            if date_key not in schedule_by_date:
                schedule_by_date[date_key] = []

            # Load shift users
            await db.refresh(shift, ['users'])
            for shift_user in shift.users:
                schedule_obj = Schedule(
                    team_id=shift.team_id,
                    user_id=shift_user.id,
                    date=shift.date,
                    notes="Shift"
                )
                schedule_by_date[date_key].append(schedule_obj)

        # Build response days array
        days = []
        current_date = start_date
        while current_date < end_date:
            date_key = current_date.isoformat()
            users_list = []
            notes = None

            if date_key in schedule_by_date:
                seen_users = set()
                for schedule in schedule_by_date[date_key]:
                    if schedule.user_id not in seen_users:
                        users_list.append({
                            "id": schedule.user.id,
                            "telegram_id": schedule.user.telegram_username,
                            "first_name": schedule.user.display_name,
                            "last_name": "",
                            "username": schedule.user.telegram_username
                        })
                        seen_users.add(schedule.user_id)
                    if schedule.notes and not notes:
                        notes = schedule.notes

            days.append({
                "date": date_key,
                "users": users_list,
                "notes": notes
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

        # Get schedules for this date
        schedules_stmt = select(Schedule).where(
            and_(
                Schedule.date == date_obj,
                Schedule.team.has(Team.workspace_id == user.workspace_id)
            )
        )
        schedules = (await db.execute(schedules_stmt)).scalars().all()

        # Get shifts for this date
        shifts_stmt = select(Shift).where(
            and_(
                Shift.date == date_obj,
                Shift.team.has(Team.workspace_id == user.workspace_id)
            )
        )
        shifts = (await db.execute(shifts_stmt)).scalars().all()

        users_list = []
        seen_users = set()
        notes = None

        # Add users from schedules
        for schedule in schedules:
            if schedule.user_id not in seen_users:
                await db.refresh(schedule, ['user'])
                users_list.append({
                    "id": schedule.user.id,
                    "telegram_id": schedule.user.telegram_username,
                    "first_name": schedule.user.display_name,
                    "last_name": "",
                    "username": schedule.user.telegram_username
                })
                seen_users.add(schedule.user_id)
            if schedule.notes and not notes:
                notes = schedule.notes

        # Add users from shifts
        for shift in shifts:
            await db.refresh(shift, ['users'])
            for shift_user in shift.users:
                if shift_user.id not in seen_users:
                    users_list.append({
                        "id": shift_user.id,
                        "telegram_id": shift_user.telegram_username,
                        "first_name": shift_user.display_name,
                        "last_name": "",
                        "username": shift_user.telegram_username
                    })
                    seen_users.add(shift_user.id)

        return {
            "date": date,
            "users": users_list,
            "notes": notes
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
