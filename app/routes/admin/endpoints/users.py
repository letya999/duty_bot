"""User management endpoints"""
import logging
from pydantic import BaseModel
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import get_db, get_current_user
from app.models import User
from app.services.user_service import UserService
from app.services.admin_service import AdminService
from app.repositories import UserRepository, AdminLogRepository
from app.routes.admin.dependencies import get_user_service, get_admin_service

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/users", tags=["Users"])


class UserUpdateRequest(BaseModel):
    display_name: str | None = None
    first_name: str | None = None
    last_name: str | None = None


@router.get(
    "/info",
    summary="Get current user information",
    description="Получить информацию о текущем авторизованном пользователе. Требует валидный Bearer token."
)
async def get_user_info(user: User = Depends(get_current_user)) -> dict:
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
    "",
    summary="List all users",
    description="Получить список всех пользователей в workspace."
)
async def get_all_users(
    user: User = Depends(get_current_user),
    user_service: UserService = Depends(get_user_service)
) -> list:
    """Get all users in workspace"""
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
    "/{user_id}",
    summary="Update user information",
    description="Обновить информацию о пользователе (например, display_name)."
)
async def update_user_info(
    user_id: int,
    data: UserUpdateRequest,
    user: User = Depends(get_current_user),
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


@router.get(
    "/admins",
    summary="List all admins",
    description="Получить список всех администраторов в workspace."
)
async def get_admins(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> dict:
    """Get list of all admins in workspace"""
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
    "/{user_id}/promote",
    summary="Promote user to admin",
    description="Повысить прав пользователя до администратора."
)
async def promote_user(
    user_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    admin_service: AdminService = Depends(get_admin_service)
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
    "/{user_id}/demote",
    summary="Demote user from admin",
    description="Удалить права администратора у пользователя."
)
async def demote_user(
    user_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    admin_service: AdminService = Depends(get_admin_service)
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
