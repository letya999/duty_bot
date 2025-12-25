from app.models import AdminLog, User
from app.repositories import AdminLogRepository, UserRepository
from app.config import get_settings
from datetime import datetime
import json


class AdminService:
    """Manage admin operations and audit logs"""

    def __init__(self, admin_log_repo: AdminLogRepository, user_repo: UserRepository):
        self.admin_log_repo = admin_log_repo
        self.user_repo = user_repo
        self.settings = get_settings()

    async def check_permission(self, user_id: int, workspace_id: int, action: str) -> bool:
        """
        Check if user has permission for action.
        If user is in master admin list (env), always allow.
        Otherwise, check if user is admin in this workspace.
        """
        user_obj = await self.user_repo.get_by_id(user_id)
        if not user_obj:
            return False

        # Check master admin status
        admin_telegram_ids = self.settings.get_admin_ids('telegram')
        admin_slack_ids = self.settings.get_admin_ids('slack')

        if user_obj.telegram_id and str(user_obj.telegram_id) in admin_telegram_ids:
            return True
        if user_obj.slack_user_id and user_obj.slack_user_id in admin_slack_ids:
            return True

        # If no master admins configured at all, and no admins in workspace, 
        # we might want a fallback, but for now just check is_admin flag
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
        details_str = json.dumps(details) if details else None
        return await self.admin_log_repo.log_action(
            workspace_id=workspace_id,
            admin_user_id=admin_id,
            action=action,
            target_user_id=target_user_id,
            details=details_str
        )

    async def get_action_history(self, workspace_id: int, limit: int = 100) -> list[AdminLog]:
        """Get recent admin actions"""
        return await self.admin_log_repo.list_by_workspace(workspace_id, limit)

    async def get_user_action_history(
        self, user_id: int, workspace_id: int, limit: int = 50
    ) -> list[AdminLog]:
        """Get action history for a specific user (both as admin and target)"""
        # Get logs where user is admin
        admin_logs = await self.admin_log_repo.list_by_admin(workspace_id, user_id, limit)
        # Get logs where user is target
        target_logs = await self.admin_log_repo.list_by_target_user(workspace_id, user_id, limit)

        # Merge and sort by timestamp
        all_logs = admin_logs + target_logs
        all_logs.sort(key=lambda x: x.timestamp, reverse=True)
        return all_logs[:limit]
