"""Statistics and reports endpoints"""
import logging
from datetime import timedelta, datetime
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import get_db, get_current_user
from app.models import User
from app.services.schedule_service import ScheduleService
from app.services.team_service import TeamService
from app.services.stats_service import StatsService
from app.repositories import ScheduleRepository, TeamRepository
from app.config.api_utils import get_schedules_for_period
from app.routes.admin.dependencies import (
    get_schedule_service,
    get_team_service,
    get_stats_service
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/stats", tags=["Statistics"])
schedules_router = APIRouter(prefix="/schedules", tags=["Schedules"])


@schedules_router.get(
    "/range",
    summary="Get schedules by date range",
    description="Получить все дежурства в диапазоне дат."
)
async def get_schedules_by_date_range(
    start_date: str,
    end_date: str,
    user: User = Depends(get_current_user),
    schedule_service: ScheduleService = Depends(get_schedule_service),
    team_service: TeamService = Depends(get_team_service),
    db: AsyncSession = Depends(get_db)
) -> dict:
    """Get all schedules within a date range"""
    try:
        from datetime import datetime as dt

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
    "/schedules",
    summary="Get schedule statistics",
    description="Получить статистику по дежурствам за период (по умолчанию последние 30 дней)."
)
async def get_schedule_statistics(
    start_date: str = None,
    end_date: str = None,
    user: User = Depends(get_current_user),
    stats_service: StatsService = Depends(get_stats_service),
    schedule_service: ScheduleService = Depends(get_schedule_service),
    team_service: TeamService = Depends(get_team_service)
) -> dict:
    """Get schedule statistics"""
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


@router.get(
    "/admin-logs",
    summary="Get admin action logs",
    description="Получить логи всех действий администраторов."
)
async def get_admin_logs(
    limit: int = 50,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> dict:
    """Get recent admin action logs"""
    try:
        from app.services.admin_service import AdminService
        from app.repositories import AdminLogRepository

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
