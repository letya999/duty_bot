"""Google Calendar integration endpoints"""
import logging
from typing import Optional, List
from pydantic import BaseModel
from fastapi import APIRouter, Depends, HTTPException, Header
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import (
    get_db,
    get_current_user,
    get_user_repository,
    get_google_calendar_repository,
    get_schedule_repository,
    get_team_repository,
)
from app.models import User
from app.services.google_calendar_service import GoogleCalendarService
from app.repositories import (
    UserRepository,
    GoogleCalendarRepository,
    ScheduleRepository,
    TeamRepository
)
from app.routes.admin.dependencies import get_google_calendar_service

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/settings/google-calendar", tags=["Google Calendar"])


class ServiceAccountKeyRequest(BaseModel):
    """Request model for service account key upload."""
    service_account_key: dict
    team_ids: Optional[List[int]] = None


async def get_user_from_token(
    token: str,
    user_repo: UserRepository
) -> User:
    """Extract user from token"""
    from app.auth import session_manager

    if not token or not token.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Invalid token format")

    token = token.replace("Bearer ", "")
    session = await session_manager.validate_session(token)

    if not session:
        raise HTTPException(status_code=401, detail="Invalid or expired token")

    user = await user_repo.get_by_id(session.get("user_id"))
    if not user:
        raise HTTPException(status_code=401, detail="User not found")

    return user


@router.get(
    "/status",
    summary="Get Google Calendar integration status",
    description="Получить список интеграций с Google Calendar."
)
async def get_google_calendar_status(
    user: User = Depends(get_current_user),
    google_calendar_repo: GoogleCalendarRepository = Depends(get_google_calendar_repository),
    team_repo: TeamRepository = Depends(get_team_repository)
) -> dict:
    """Get Google Calendar integration status."""
    try:
        if not user.is_admin:
            raise HTTPException(status_code=403, detail="Only admins can access this endpoint")

        integrations = await google_calendar_repo.list_by_workspace(user.workspace_id)
        
        result_list = []
        for integration in integrations:
            team_names = "All Teams"
            team_ids_list = []
            if integration.teams:
                team_names = ", ".join([t.display_name for t in integration.teams])
                team_ids_list = [t.id for t in integration.teams]
            
            result_list.append({
                "id": integration.id,
                "is_active": integration.is_active,
                "public_calendar_url": integration.public_calendar_url,
                "service_account_email": integration.service_account_email,
                "last_sync_at": integration.last_sync_at.isoformat() if integration.last_sync_at else None,
                "google_calendar_id": integration.google_calendar_id,
                "team_ids": team_ids_list,
                "team_name": team_names
            })

        return {
            "integrations": result_list,
            "is_connected": len(result_list) > 0,
            "workspace_id": user.workspace_id
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting Google Calendar status: {e}")
        raise HTTPException(status_code=500, detail="Failed to get Google Calendar status")


@router.post(
    "/setup",
    summary="Setup Google Calendar integration",
    description="Установить интеграцию с Google Calendar через service account."
)
async def setup_google_calendar(
    request: ServiceAccountKeyRequest,
    authorization: str = Header(None),
    user_repo: UserRepository = Depends(get_user_repository),
    google_calendar_repo: GoogleCalendarRepository = Depends(get_google_calendar_repository),
    schedule_repo: ScheduleRepository = Depends(get_schedule_repository),
    team_repo: TeamRepository = Depends(get_team_repository)
) -> dict:
    """Setup Google Calendar integration."""
    try:
        user = await get_user_from_token(authorization, user_repo)

        if not user.is_admin:
            raise HTTPException(status_code=403, detail="Only admins can access this endpoint")

        # For multiple calendars support, checking "already configured" is tricky.
        # We allow multiple. If they upload the same JSON again, it creates a new calendar.
        # User is responsible for deleting old ones if they want to replace.
        
        google_service = GoogleCalendarService(google_calendar_repo)

        integration = await google_service.setup_google_calendar(
            user.workspace_id,
            request.service_account_key,
            request.team_ids
        )
        
        # Manually add teams here since we didn't inject TeamRepo into service fully
        if request.team_ids:
            teams_objects = []
            for tid in request.team_ids:
                t = await team_repo.get_by_id(tid)
                if t:
                    teams_objects.append(t)
            if teams_objects:
                await google_calendar_repo.add_teams(integration, teams_objects)

        # Trigger initial sync of existing/future schedules
        synced_count = await google_service.sync_workspace_schedules(
            user.workspace_id,
            schedule_repo,
            team_repo
        )
        logger.info(f"Initial sync after setup: {synced_count} schedules synced")

        return {
            "status": "success",
            "public_calendar_url": integration.public_calendar_url,
            "google_calendar_id": integration.google_calendar_id,
            "service_account_email": integration.service_account_email,
            "synced_count": synced_count
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error setting up Google Calendar: {e}")
        raise HTTPException(status_code=400, detail=str(e))


@router.delete(
    "/{integration_id}",
    summary="Disconnect Google Calendar integration",
    description="Отключить интеграцию с Google Calendar (удалить конкретный календарь)."
)
async def disconnect_google_calendar(
    integration_id: int,
    user: User = Depends(get_current_user),
    google_calendar_repo: GoogleCalendarRepository = Depends(get_google_calendar_repository)
) -> dict:
    """Disconnect Google Calendar integration."""
    try:
        if not user.is_admin:
            raise HTTPException(status_code=403, detail="Only admins can access this endpoint")

        google_service = GoogleCalendarService(google_calendar_repo)

        # Verify integration belongs to workspace (implicitly done via repo lookup but let's be safe if we had checks)
        # Service disconnect deletes by ID after check
        success = await google_service.disconnect_google_calendar(integration_id)

        if not success:
            raise HTTPException(status_code=404, detail="Google Calendar integration not found")

        return {"status": "disconnected"}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error disconnecting Google Calendar: {e}")
        raise HTTPException(status_code=500, detail="Failed to disconnect Google Calendar")


@router.get(
    "/url",
    summary="Get public calendar URLs",
    description="Получить публичные URL календарей."
)
async def get_public_calendar_url(
    user: User = Depends(get_current_user),
    google_calendar_repo: GoogleCalendarRepository = Depends(get_google_calendar_repository)
) -> dict:
    """Get public Google Calendar URLs."""
    try:
        integrations = await google_calendar_repo.list_by_workspace(user.workspace_id)
        
        if not integrations:
             raise HTTPException(status_code=404, detail="Google Calendar not configured")

        # Return list or the first one if legacy client?
        # Let's return list
        urls = []
        for i in integrations:
            if i.is_active:
                urls.append({
                    "url": i.public_calendar_url,
                    "calendar_id": i.google_calendar_id,
                    "team_ids": [t.id for t in i.teams] if i.teams else []
                })
        
        return {
            "calendars": urls
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting calendar URL: {e}")
        raise HTTPException(status_code=500, detail="Failed to get calendar URL")


@router.post(
    "/sync",
    summary="Manually trigger Google Calendar sync",
    description="Вручную запустить синхронизацию дежурств с Google Calendar."
)
async def sync_google_calendar(
    user: User = Depends(get_current_user),
    google_calendar_repo: GoogleCalendarRepository = Depends(get_google_calendar_repository),
    schedule_repo: ScheduleRepository = Depends(get_schedule_repository),
    team_repo: TeamRepository = Depends(get_team_repository)
) -> dict:
    """Manually trigger Google Calendar sync."""
    try:
        if not user.is_admin:
            raise HTTPException(status_code=403, detail="Only admins can access this endpoint")

        google_service = GoogleCalendarService(google_calendar_repo)

        synced_count = await google_service.sync_workspace_schedules(
            user.workspace_id,
            schedule_repo,
            team_repo
        )

        return {
            "status": "success",
            "synced_count": synced_count
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error syncing Google Calendar: {e}")
        raise HTTPException(status_code=500, detail="Failed to sync Google Calendar")
