from app.models import User
from app.repositories import UserRepository, AdminLogRepository


class UserService:
    def __init__(self, user_repo: UserRepository, admin_log_repo: AdminLogRepository = None):
        self.user_repo = user_repo
        self.admin_log_repo = admin_log_repo

    async def create_user(self, workspace_id: int, username: str, telegram_username: str = None, first_name: str = None, last_name: str = None, slack_user_id: str = None) -> User:
        """Create a new user"""
        return await self.user_repo.create({
            'workspace_id': workspace_id,
            'username': username,
            'telegram_username': telegram_username,
            'first_name': first_name,
            'last_name': last_name,
            'slack_user_id': slack_user_id,
            'display_name': first_name or username
        })
    async def get_or_create_by_telegram(self, workspace_id: int, telegram_username: str, display_name: str, first_name: str = None, last_name: str = None, telegram_id: int = None) -> User:
        """Get or create user by Telegram username or ID in workspace"""
        # Try to find by telegram_id first if provided
        if telegram_id:
            user = await self.user_repo.get_by_telegram_id(workspace_id, telegram_id)
            if user:
                return user

        # Try to find by telegram_username
        user = await self.user_repo.get_by_telegram_username(workspace_id, telegram_username)

        if not user:
            user = await self.user_repo.create({
                'workspace_id': workspace_id,
                'telegram_id': telegram_id,
                'telegram_username': telegram_username,
                'display_name': display_name,
                'first_name': first_name,
                'last_name': last_name,
            })
        else:
            # Update telegram_id if it wasn't set before
            if telegram_id and not user.telegram_id:
                user = await self.user_repo.update(user.id, {'telegram_id': telegram_id})

        return user

    async def get_or_create_by_slack(self, workspace_id: int, slack_user_id: str, display_name: str, first_name: str = None, last_name: str = None) -> User:
        """Get or create user by Slack user ID in workspace"""
        user = await self.user_repo.get_by_slack_user_id(workspace_id, slack_user_id)

        if not user:
            user = await self.user_repo.create({
                'workspace_id': workspace_id,
                'slack_user_id': slack_user_id,
                'display_name': display_name,
                'first_name': first_name,
                'last_name': last_name,
            })

        return user

    async def get_user(self, user_id: int, workspace_id: int = None) -> User | None:
        """Get user by ID, optionally filtered by workspace"""
        user = await self.user_repo.get_by_id(user_id)
        if user and workspace_id is not None and user.workspace_id != workspace_id:
            return None
        return user

    async def get_user_by_telegram(self, workspace_id: int, telegram_username: str) -> User | None:
        """Get user by Telegram username in workspace"""
        return await self.user_repo.get_by_telegram_username(workspace_id, telegram_username)

    async def get_user_by_slack(self, workspace_id: int, slack_user_id: str) -> User | None:
        """Get user by Slack user ID in workspace"""
        return await self.user_repo.get_by_slack_user_id(workspace_id, slack_user_id)

    async def get_all_users(self, workspace_id: int) -> list[User]:
        """Get all users in workspace"""
        return await self.user_repo.list_by_workspace(workspace_id)

    async def promote_user(self, user_id: int, workspace_id: int, admin_user_id: int = None) -> User:
        """Promote user to admin with audit logging"""
        user = await self.user_repo.update_admin_status(user_id, True)
        if user and self.admin_log_repo and admin_user_id:
            await self.admin_log_repo.log_action(
                workspace_id=workspace_id,
                admin_user_id=admin_user_id,
                action='promoted_admin',
                target_user_id=user_id,
                details=f'Promoted {user.display_name} to admin'
            )
        return user

    async def demote_user(self, user_id: int, workspace_id: int, admin_user_id: int = None) -> User:
        """Demote user from admin with audit logging"""
        user = await self.user_repo.update_admin_status(user_id, False)
        if user and self.admin_log_repo and admin_user_id:
            await self.admin_log_repo.log_action(
                workspace_id=workspace_id,
                admin_user_id=admin_user_id,
                action='demoted_admin',
                target_user_id=user_id,
                details=f'Demoted {user.display_name} from admin'
            )
        return user

    async def set_admin(self, user_id: int, is_admin: bool) -> User:
        """Set or unset admin status for a user"""
        return await self.user_repo.update_admin_status(user_id, is_admin)

    async def get_all_admins(self, workspace_id: int) -> list[User]:
        """Get all admin users in workspace"""
        return await self.user_repo.list_admins_in_workspace(workspace_id)

    async def is_admin(self, user_id: int) -> bool:
        """Check if user is admin"""
        user = await self.user_repo.get_by_id(user_id)
        return user.is_admin if user else False
