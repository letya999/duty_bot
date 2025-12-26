"""Shared utility functions for API endpoints to reduce duplication"""
from datetime import datetime, timedelta
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload
from app.models import Schedule, Team, User, Workspace


async def format_user_response(user: User) -> dict:
    """Format user object to API response"""
    if not user:
        return {"id": 0, "telegram_id": "", "first_name": "Unknown", "last_name": "", "username": ""}
    return {
        "id": user.id,
        "telegram_id": user.telegram_username,
        "first_name": user.display_name or user.first_name,
        "last_name": user.last_name or "",
        "username": user.telegram_username or user.username
    }


async def get_workspace_by_user(db: AsyncSession, user: User) -> Workspace:
    """Get workspace for a user"""
    return user.workspace


async def get_month_dates(year: int, month: int) -> tuple:
    """Get start and end dates for a month (inclusive)"""
    start_date = datetime(year, month, 1).date()
    if month == 12:
        next_month_first = datetime(year + 1, 1, 1).date()
    else:
        next_month_first = datetime(year, month + 1, 1).date()
    
    end_date = next_month_first - timedelta(days=1)
    return start_date, end_date


async def get_schedules_for_period(
    db: AsyncSession,
    user: User,
    start_date,
    end_date
) -> list[Schedule]:
    """Get all schedules for a date period for user's workspace (both dates inclusive)"""
    stmt = select(Schedule).join(Team).where(
        and_(
            Schedule.date >= start_date,
            Schedule.date <= end_date,
            Team.workspace_id == user.workspace_id
        )
    ).options(joinedload(Schedule.user), joinedload(Schedule.team))
    result = await db.execute(stmt)
    return result.scalars().all()


async def build_schedule_by_date(schedules: list) -> dict:
    """Group schedules by date"""
    schedule_by_date = {}
    for schedule in schedules:
        date_key = schedule.date.isoformat()
        if date_key not in schedule_by_date:
            schedule_by_date[date_key] = []
        schedule_by_date[date_key].append(schedule)
    return schedule_by_date


async def build_days_array(
    start_date,
    end_date,
    schedule_by_date: dict
) -> list:
    """Build API response days array from schedule data"""
    days = []
    current_date = start_date

    while current_date <= end_date:
        date_key = current_date.isoformat()
        users_list = []
        notes = None

        if date_key in schedule_by_date:
            for schedule in schedule_by_date[date_key]:
                users_list.append(await format_user_response(schedule.user))
                if schedule.is_shift:
                    notes = "Shift"

        days.append({
            "date": date_key,
            "users": users_list,
            "notes": notes
        })
        current_date += timedelta(days=1)

    return days


async def get_daily_schedules(
    db: AsyncSession,
    user: User,
    date_obj
) -> list[Schedule]:
    """Get schedules for a specific day"""
    stmt = select(Schedule).join(Team).where(
        and_(
            Schedule.date == date_obj,
            Team.workspace_id == user.workspace_id
        )
    ).options(joinedload(Schedule.user), joinedload(Schedule.team))
    result = await db.execute(stmt)
    return result.scalars().all()


async def build_daily_users_list(
    schedules: list
) -> dict:
    """Build users list for a day from schedules"""
    users_list = []
    for schedule in schedules:
        user_response = await format_user_response(schedule.user)
        # Add metadata if needed (e.g. which team)
        users_list.append(user_response)

    return {
        "users": users_list,
        "count": len(users_list)
    }

