from app.models import User
from app.repositories import UserRepository, AdminLogRepository


class UserService:
    def __init__(self, user_repo: UserRepository, admin_log_repo: AdminLogRepository = None):
        self.user_repo = user_repo
        self.admin_log_repo = admin_log_repo

    async def create_user(self, workspace_id: int, username: str, telegram_username: str = None, first_name: str = None, last_name: str = None, slack_user_id: str = None, telegram_id: int = None, display_name: str = None) -> User:
        """Create a new user"""
        return await self.user_repo.create({
            'workspace_id': workspace_id,
            'username': username,
            'telegram_username': telegram_username,
            'first_name': first_name,
            'last_name': last_name,
            'slack_user_id': slack_user_id,
            'telegram_id': telegram_id,
            'display_name': display_name or first_name or username
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
            # Use get_settings to check for master admins
            from app.config import get_settings
            settings = get_settings()
            is_master = False
            if telegram_id and str(telegram_id) in settings.get_admin_ids('telegram'):
                is_master = True

            user = await self.user_repo.create({
                'workspace_id': workspace_id,
                'telegram_id': telegram_id,
                'telegram_username': telegram_username,
                'username': telegram_username or (str(telegram_id) if telegram_id else None),
                'display_name': display_name,
                'first_name': first_name,
                'last_name': last_name,
                'is_admin': is_master
            })
        else:
            # Update info if it was missing
            update_data = {}
            if telegram_id and not user.telegram_id:
                update_data['telegram_id'] = telegram_id
            if telegram_username and not user.telegram_username:
                update_data['telegram_username'] = telegram_username
            if not user.username:
                update_data['username'] = telegram_username or (str(telegram_id) if telegram_id else None)
            if first_name and not user.first_name:
                update_data['first_name'] = first_name
            if last_name and not user.last_name:
                update_data['last_name'] = last_name
            
            # Sync master admin status
            from app.config import get_settings
            settings = get_settings()
            if telegram_id and str(telegram_id) in settings.get_admin_ids('telegram') and not user.is_admin:
                update_data['is_admin'] = True
            
            if update_data:
                user = await self.user_repo.update(user.id, update_data)

        return user

    async def get_or_create_by_slack(self, workspace_id: int, slack_user_id: str, display_name: str, first_name: str = None, last_name: str = None) -> User:
        """Get or create user by Slack user ID in workspace"""
        user = await self.user_repo.get_by_slack_user_id(workspace_id, slack_user_id)

        if not user:
            user = await self.user_repo.create({
                'workspace_id': workspace_id,
                'slack_user_id': slack_user_id,
                'username': slack_user_id,
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
        """Get user by Telegram username in workspace, fetch from TG and create/update if needed"""
        # 1. Try to find in current workspace
        user = await self.user_repo.get_by_telegram_username(workspace_id, telegram_username)
        
        # 2. Try to find anywhere else to get user info if not found in current workspace
        anywhere_user = None
        if not user:
            anywhere_user = await self.user_repo.find_anywhere_by_telegram_username(telegram_username)
            
        # 3. Prepare initial info
        info = {
            "telegram_id": (user.telegram_id if user else None) or (anywhere_user.telegram_id if anywhere_user else None),
            "first_name": (user.first_name if user else None) or (anywhere_user.first_name if anywhere_user else telegram_username),
            "last_name": (user.last_name if user else None) or (anywhere_user.last_name if anywhere_user else None),
            "display_name": (user.display_name if user else None) or (anywhere_user.display_name if anywhere_user else telegram_username)
        }

        # 4. If Telegram ID is missing, try to fetch it from Telegram Bot API
        from app.config import get_settings
        settings = get_settings()
        if not info["telegram_id"] and settings.telegram_token:
            try:
                from telegram import Bot
                import logging
                logger = logging.getLogger(__name__)
                
                bot = Bot(token=settings.telegram_token)
                # get_chat works for users with public usernames if the bot has seen them or they are in the same chat
                chat = await bot.get_chat(f"@{telegram_username}")
                info["telegram_id"] = chat.id
                info["first_name"] = chat.first_name or info["first_name"]
                info["last_name"] = chat.last_name or info["last_name"]
                if chat.first_name:
                    info["display_name"] = f"{chat.first_name} {chat.last_name or ''}".strip()
                else:
                    info["display_name"] = chat.username or info["display_name"]
                
                logger.info(f"Fetched Telegram info for @{telegram_username}: {info['telegram_id']}")
            except Exception as e:
                import logging
                logging.getLogger(__name__).warning(f"Failed to fetch Telegram info for {telegram_username}: {e}")

        # 5. Create or update record in this workspace
        return await self.get_or_create_by_telegram(
            workspace_id,
            telegram_username,
            info["display_name"],
            first_name=info["first_name"],
            last_name=info["last_name"],
            telegram_id=info["telegram_id"]
        )

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

    async def update_user(self, user_id: int, workspace_id: int, update_data: dict) -> User | None:
        """Update user information"""
        user = await self.user_repo.get_by_id(user_id)
        if not user or user.workspace_id != workspace_id:
            return None
        return await self.user_repo.update(user_id, update_data)
