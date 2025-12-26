"""Team management endpoints"""
import logging
from fastapi import APIRouter, Depends, HTTPException, Body
from sqlalchemy import select, or_
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import get_db, get_current_user
from app.models import User
from app.services.team_service import TeamService
from app.services.user_service import UserService
from app.repositories import TeamRepository, UserRepository
from app.exceptions import NotFoundError
from app.routes.admin.dependencies import get_team_service, get_user_service

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/teams", tags=["Teams"])


@router.get(
    "",
    summary="List all teams",
    description="Получить список всех команд в workspace с информацией о членах."
)
async def get_teams(
    user: User = Depends(get_current_user),
    team_service: TeamService = Depends(get_team_service)
) -> list:
    """Get all teams in workspace"""
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


@router.get("/{team_id}/members")
async def get_team_members(
    team_id: int,
    user: User = Depends(get_current_user),
    team_service: TeamService = Depends(get_team_service)
) -> list:
    """Get all members of a team"""
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
        raise HTTPException(status_code=500, detail="Failed to get team members")


@router.post(
    "",
    summary="Create new team",
    description="Создать новую команду в workspace."
)
async def create_team(
    name: str = Body(..., embed=False),
    display_name: str = Body(..., embed=False),
    has_shifts: bool = Body(False, embed=False),
    team_lead_id: int | None = Body(None, embed=False),
    user: User = Depends(get_current_user),
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
    "/{team_id}",
    summary="Update team",
    description="Обновить информацию о команде (название, описание, настройки)."
)
async def update_team(
    team_id: int,
    name: str | None = Body(None, embed=False),
    display_name: str | None = Body(None, embed=False),
    has_shifts: bool | None = Body(None, embed=False),
    team_lead_id: int | None = Body(None, embed=False),
    user: User = Depends(get_current_user),
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
    "/{team_id}",
    summary="Delete team",
    description="Удалить команду из workspace."
)
async def delete_team(
    team_id: int,
    user: User = Depends(get_current_user),
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
    "/{team_id}/members",
    summary="Add team member",
    description="Добавить пользователя в команду."
)
async def add_team_member(
    team_id: int,
    user_id: int = Body(..., embed=True),
    user: User = Depends(get_current_user),
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
    "/{team_id}/members/{member_id}",
    summary="Remove team member",
    description="Удалить пользователя из команды."
)
async def remove_team_member(
    team_id: int,
    member_id: int,
    user: User = Depends(get_current_user),
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


@router.post(
    "/{team_id}/members/import",
    summary="Import member by handle",
    description="Добавить участника по Telegram/Slack нику или ссылке."
)
async def import_team_member(
    team_id: int,
    handle: str = Body(..., embed=True),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> dict:
    """Import member by handle"""
    try:
        from telegram import Bot
        from slack_sdk.web.async_client import AsyncWebClient
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
                    logger.info(f"Attempting to fetch Telegram info for @{clean_handle}")
                    chat = await bot.get_chat(f"@{clean_handle}")
                    imported_info["first_name"] = chat.first_name or clean_handle
                    imported_info["last_name"] = chat.last_name
                    imported_info["username"] = chat.username or clean_handle
                    imported_info["telegram_id"] = str(chat.id)
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

            if "slack.com" in clean_handle and "/team/" in clean_handle:
                parts = clean_handle.split("/team/")
                if len(parts) > 1:
                    slack_user_id = parts[1].split("/")[0].split("?")[0]

            imported_info["slack_id"] = slack_user_id

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


@router.post(
    "/members/move",
    summary="Move member to another team",
    description="Переместить участника из одной команды в другую."
)
async def move_team_member(
    user_id: int = Body(..., embed=True),
    from_team_id: int = Body(..., embed=True),
    to_team_id: int = Body(..., embed=True),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> dict:
    """Move member between teams"""
    try:
        if not user.is_admin:
            raise HTTPException(status_code=403, detail="Only admins can manage team members")

        team_service = TeamService(TeamRepository(db))

        from_team = await team_service.get_team(from_team_id, user.workspace_id)
        to_team = await team_service.get_team(to_team_id, user.workspace_id)

        if not from_team or not to_team:
            raise HTTPException(status_code=404, detail="Team not found")

        target_user = await db.get(User, user_id)
        if not target_user:
            raise HTTPException(status_code=404, detail="User not found")

        await team_service.remove_member(from_team.id, target_user)
        await team_service.add_member(to_team.id, target_user)

        return {"status": "moved"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error moving team member: {e}")
        raise HTTPException(status_code=500, detail="Failed to move team member")
