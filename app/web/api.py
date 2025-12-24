"""API endpoints for web admin panel"""
import logging
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException, Header
from sqlalchemy import select, and_, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from app.database import AsyncSessionLocal
from app.models import User, Team, Schedule, Shift, Workspace, team_members
from app.web.auth import session_manager

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/admin", tags=["admin"])


async def get_db():
    """Get database session"""
    async with AsyncSessionLocal() as session:
        yield session


async def get_user_from_token(
    authorization: str = Header(None),
    db: AsyncSession = Depends(get_db)
) -> tuple[User, dict]:
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

    return user, session


# ============ User Endpoints ============

@router.get("/user/info")
async def get_user_info(user: User = Depends(lambda auth, db: get_user_from_token(auth, db)[0])) -> dict:
    """Get current user info"""
    return {
        "id": user.id,
        "username": user.username,
        "first_name": user.first_name,
        "last_name": user.last_name or "",
        "is_admin": user.is_admin,
        "workspace_id": user.workspace_id,
    }


@router.get("/users")
async def get_all_users(
    user: User = Depends(lambda auth, db: get_user_from_token(auth, db)[0]),
    db: AsyncSession = Depends(get_db)
) -> list:
    """Get all users in workspace"""
    try:
        stmt = select(User).where(User.workspace_id == user.workspace_id)
        result = await db.execute(stmt)
        users = result.scalars().all()

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

@router.get("/teams")
async def get_teams(
    user: User = Depends(lambda auth, db: get_user_from_token(auth, db)[0]),
    db: AsyncSession = Depends(get_db)
) -> list:
    """Get all teams in workspace"""
    try:
        stmt = select(Team).where(Team.workspace_id == user.workspace_id)
        result = await db.execute(stmt)
        teams = result.scalars().all()

        result_list = []
        for team in teams:
            result_list.append({
                "id": team.id,
                "name": team.display_name or team.name,
                "description": team.description or "",
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
    user: User = Depends(lambda auth, db: get_user_from_token(auth, db)[0]),
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

@router.get("/schedule/month")
async def get_month_schedule(
    year: int,
    month: int,
    user: User = Depends(lambda auth, db: get_user_from_token(auth, db)[0]),
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
        ).options(joinedload(Schedule.user), joinedload(Schedule.team))

        result = await db.execute(schedules_stmt)
        schedules = result.unique().scalars().all()

        # Group schedules by date
        schedule_by_date = {}
        for schedule in schedules:
            date_key = schedule.date.isoformat()
            if date_key not in schedule_by_date:
                schedule_by_date[date_key] = []
            schedule_by_date[date_key].append(schedule)

        # Also get shifts for the month
        shifts_stmt = select(Shift).where(
            and_(
                Shift.date >= start_date,
                Shift.date < end_date,
                Shift.team.has(Team.workspace_id == user.workspace_id)
            )
        ).options(joinedload(Shift.users), joinedload(Shift.team))

        result = await db.execute(shifts_stmt)
        shifts = result.unique().scalars().all()

        # Add shift users to schedule_by_date
        for shift in shifts:
            date_key = shift.date.isoformat()
            if date_key not in schedule_by_date:
                schedule_by_date[date_key] = []

            # Shift users are already loaded
            for shift_user in (shift.users or []):
                schedule_obj = Schedule(
                    team_id=shift.team_id,
                    user_id=shift_user.id,
                    date=shift.date,
                    notes="Shift"
                )
                schedule_obj.user = shift_user
                schedule_obj.team = shift.team
                schedule_by_date[date_key].append(schedule_obj)

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


@router.get("/schedule/day/{date}")
async def get_daily_schedule(
    date: str,
    user: User = Depends(lambda auth, db: get_user_from_token(auth, db)[0]),
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
        ).options(joinedload(Schedule.user), joinedload(Schedule.team))

        result = await db.execute(schedules_stmt)
        schedules = result.unique().scalars().all()

        # Get shifts for this date
        shifts_stmt = select(Shift).where(
            and_(
                Shift.date == date_obj,
                Shift.team.has(Team.workspace_id == user.workspace_id)
            )
        ).options(joinedload(Shift.users), joinedload(Shift.team))

        result = await db.execute(shifts_stmt)
        shifts = result.unique().scalars().all()

        duties = []
        seen_users = set()

        # Add users from schedules
        for schedule in schedules:
            if schedule.user_id not in seen_users:
                duties.append({
                    "id": schedule.id,
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

        # Add users from shifts
        for shift in shifts:
            for shift_user in (shift.users or []):
                if shift_user.id not in seen_users:
                    duties.append({
                        "id": 0,
                        "user": {
                            "id": shift_user.id,
                            "username": shift_user.username,
                            "first_name": shift_user.first_name,
                            "last_name": shift_user.last_name or "",
                        },
                        "team": {
                            "id": shift.team.id if shift.team else None,
                            "name": shift.team.display_name or shift.team.name if shift.team else None,
                        } if shift.team else None,
                        "notes": "Shift",
                    })
                    seen_users.add(shift_user.id)

        return {
            "date": date,
            "duties": duties,
        }
    except Exception as e:
        logger.error(f"Error getting daily schedule: {e}")
        raise HTTPException(status_code=500, detail="Failed to get schedule")


@router.post("/schedule/assign")
async def assign_duty(
    data: dict,
    user: User = Depends(lambda auth, db: get_user_from_token(auth, db)[0]),
    db: AsyncSession = Depends(get_db)
) -> dict:
    """Assign duty to a user for a specific date"""
    try:
        from datetime import datetime as dt

        user_id = data.get('user_id')
        duty_date = data.get('duty_date')
        team_id = data.get('team_id')

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

        date_obj = dt.fromisoformat(duty_date).date()

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
            "date": duty_date
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
    user: User = Depends(lambda auth, db: get_user_from_token(auth, db)[0]),
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


@router.get("/admins")
async def get_admins(
    user: User = Depends(lambda auth, db: get_user_from_token(auth, db)[0]),
    db: AsyncSession = Depends(get_db)
) -> dict:
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
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting admins: {e}")
        raise HTTPException(status_code=500, detail="Failed to get admins")


@router.post("/users/{user_id}/promote")
async def promote_user(
    user_id: int,
    current_user: User = Depends(lambda auth, db: get_user_from_token(auth, db)[0]),
    db: AsyncSession = Depends(get_db)
) -> dict:
    """Promote user to admin (admin only)"""
    try:
        # Check if current user is admin
        if not current_user.is_admin:
            raise HTTPException(status_code=403, detail="Only admins can promote users")

        # Get target user
        target_user = await db.get(User, user_id)
        if not target_user:
            raise HTTPException(status_code=404, detail="User not found")

        # Check same workspace
        if target_user.workspace_id != current_user.workspace_id:
            raise HTTPException(status_code=403, detail="Cannot manage users from other workspaces")

        # Promote user
        target_user.is_admin = True
        await db.commit()

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


@router.post("/users/{user_id}/demote")
async def demote_user(
    user_id: int,
    current_user: User = Depends(lambda auth, db: get_user_from_token(auth, db)[0]),
    db: AsyncSession = Depends(get_db)
) -> dict:
    """Remove admin rights from user (admin only)"""
    try:
        # Check if current user is admin
        if not current_user.is_admin:
            raise HTTPException(status_code=403, detail="Only admins can demote users")

        # Get target user
        target_user = await db.get(User, user_id)
        if not target_user:
            raise HTTPException(status_code=404, detail="User not found")

        # Check same workspace
        if target_user.workspace_id != current_user.workspace_id:
            raise HTTPException(status_code=403, detail="Cannot manage users from other workspaces")

        # Prevent demoting yourself
        if target_user.id == current_user.id:
            raise HTTPException(status_code=400, detail="Cannot demote yourself")

        # Demote user
        target_user.is_admin = False
        await db.commit()

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
