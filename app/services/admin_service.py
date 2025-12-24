from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc
from app.models import AdminLog, User
from app.config import get_settings
from datetime import datetime
import json


class AdminService:
    """Manage admin operations and audit logs"""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.settings = get_settings()

    async def check_permission(self, user_id: int, workspace_id: int, action: str) -> bool:
        """
        Check if user has permission for action.
        If no admins configured, allow all users.
        If admins configured, only admins can perform actions.
        """
        # Get admin IDs from config
        admin_ids = self.settings.get_admin_ids('telegram') + self.settings.get_admin_ids('slack')

        # If no admins configured, allow all
        if not admin_ids:
            return True

        # Check if user is admin
        user = await self.db.execute(select(User).where(User.id == user_id))
        user_obj = user.scalars().first()

        if not user_obj:
            return False

        # Check if user is in admin list by ID
        return user_obj.is_admin

    async def log_action(
        self,
        workspace_id: int,
        admin_id: int,
        action: str,
        target_user_id: int = None,
        details: dict = None,
    ) -> AdminLog:
        """Log admin action for audit trail"""
        log_entry = AdminLog(
            workspace_id=workspace_id,
            admin_user_id=admin_id,
            action=action,
            target_user_id=target_user_id,
            timestamp=datetime.utcnow(),
            details=json.dumps(details) if details else None,
        )
        self.db.add(log_entry)
        await self.db.commit()
        await self.db.refresh(log_entry)
        return log_entry

    async def get_action_history(self, workspace_id: int, limit: int = 100) -> list[AdminLog]:
        """Get recent admin actions"""
        from sqlalchemy.orm import selectinload
        stmt = (
            select(AdminLog)
            .options(
                selectinload(AdminLog.admin_user),
                selectinload(AdminLog.target_user)
            )
            .where(AdminLog.workspace_id == workspace_id)
            .order_by(desc(AdminLog.timestamp))
            .limit(limit)
        )
        result = await self.db.execute(stmt)
        return result.scalars().all()

    async def get_user_action_history(
        self, user_id: int, workspace_id: int, limit: int = 50
    ) -> list[AdminLog]:
        """Get action history for a specific user (both as admin and target)"""
        stmt = (
            select(AdminLog)
            .where(
                (AdminLog.workspace_id == workspace_id)
                & (
                    (AdminLog.admin_user_id == user_id)
                    | (AdminLog.target_user_id == user_id)
                )
            )
            .order_by(desc(AdminLog.timestamp))
            .limit(limit)
        )
        result = await self.db.execute(stmt)
        return result.scalars().all()
