"""Shared utility functions for API endpoints to reduce duplication"""
from datetime import datetime, timedelta
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession
from app.models import Schedule, Shift, Team, User, Workspace


async def format_user_response(user: User) -> dict:
    """Format user object to API response"""
    return {
        "id": user.id,
        "telegram_id": user.telegram_username,
        "first_name": user.display_name,
        "last_name": user.last_name or "",
        "username": user.telegram_username or user.username
    }


async def get_workspace_by_user(db: AsyncSession, user: User) -> Workspace:
    """Get workspace for a user"""
    return user.workspace


async def get_month_dates(year: int, month: int) -> tuple:
    """Get start and end dates for a month"""
    start_date = datetime(year, month, 1).date()
    if month == 12:
        end_date = datetime(year + 1, 1, 1).date()
    else:
        end_date = datetime(year, month + 1, 1).date()
    return start_date, end_date


async def get_schedules_and_shifts_for_period(
    db: AsyncSession,
    user: User,
    start_date,
    end_date
) -> tuple[list[Schedule], list[Shift]]:
    """Get schedules and shifts for a date period for user's workspace"""
    # Get all schedules for the period
    schedules_stmt = select(Schedule).where(
        and_(
            Schedule.date >= start_date,
            Schedule.date < end_date,
            Schedule.team.has(Team.workspace_id == user.workspace_id)
        )
    )
    schedules = (await db.execute(schedules_stmt)).scalars().all()

    # Get shifts for the period
    shifts_stmt = select(Shift).where(
        and_(
            Shift.date >= start_date,
            Shift.date < end_date,
            Shift.team.has(Team.workspace_id == user.workspace_id)
        )
    )
    shifts = (await db.execute(shifts_stmt)).scalars().all()

    return schedules, shifts


async def build_schedule_by_date(schedules: list, shifts: list, db: AsyncSession) -> dict:
    """Group schedules and shifts by date, handling deduplication"""
    schedule_by_date = {}

    # Add regular schedules
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

    return schedule_by_date


async def build_days_array(
    start_date,
    end_date,
    schedule_by_date: dict
) -> list:
    """Build API response days array from schedule data"""
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
                    users_list.append(await format_user_response(schedule.user))
                    seen_users.add(schedule.user_id)
                if schedule.notes and not notes:
                    notes = schedule.notes

        days.append({
            "date": date_key,
            "users": users_list,
            "notes": notes
        })
        current_date += timedelta(days=1)

    return days


async def get_daily_schedules_and_shifts(
    db: AsyncSession,
    user: User,
    date_obj
) -> tuple[list[Schedule], list[Shift]]:
    """Get schedules and shifts for a specific day"""
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

    return schedules, shifts


async def build_daily_users_list(
    schedules: list,
    shifts: list,
    db: AsyncSession
) -> dict:
    """Build users list for a day from schedules and shifts"""
    users_dict = {}

    # Add from schedules
    for schedule in schedules:
        if schedule.user_id not in users_dict:
            users_dict[schedule.user_id] = {
                "user": schedule.user,
                "notes": schedule.notes
            }

    # Add from shifts
    for shift in shifts:
        await db.refresh(shift, ['users'])
        for shift_user in shift.users:
            if shift_user.id not in users_dict:
                users_dict[shift_user.id] = {
                    "user": shift_user,
                    "notes": "Shift"
                }

    # Convert to list format
    users_list = []
    for user_id, data in users_dict.items():
        user_response = await format_user_response(data["user"])
        users_list.append(user_response)

    return {
        "users": users_list,
        "count": len(users_list)
    }
