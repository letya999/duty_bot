from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models import User


class UserService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_or_create_by_telegram(self, workspace_id: int, telegram_username: str, display_name: str, first_name: str = None, last_name: str = None) -> User:
        """Get or create user by Telegram username in workspace"""
        stmt = select(User).where(
            (User.workspace_id == workspace_id) &
            (User.telegram_username == telegram_username)
        )
        result = await self.db.execute(stmt)
        user = result.scalars().first()

        if not user:
            user = User(
                workspace_id=workspace_id,
                telegram_username=telegram_username,
                display_name=display_name,
                first_name=first_name,
                last_name=last_name,
            )
            self.db.add(user)
            await self.db.commit()
            await self.db.refresh(user)

        return user

    async def get_or_create_by_slack(self, workspace_id: int, slack_user_id: str, display_name: str, first_name: str = None, last_name: str = None) -> User:
        """Get or create user by Slack user ID in workspace"""
        stmt = select(User).where(
            (User.workspace_id == workspace_id) &
            (User.slack_user_id == slack_user_id)
        )
        result = await self.db.execute(stmt)
        user = result.scalars().first()

        if not user:
            user = User(
                workspace_id=workspace_id,
                slack_user_id=slack_user_id,
                display_name=display_name,
                first_name=first_name,
                last_name=last_name,
            )
            self.db.add(user)
            await self.db.commit()
            await self.db.refresh(user)

        return user

    async def get_user(self, user_id: int, workspace_id: int = None) -> User | None:
        """Get user by ID, optionally filtered by workspace"""
        stmt = select(User).where(User.id == user_id)
        if workspace_id is not None:
            stmt = stmt.where(User.workspace_id == workspace_id)
        result = await self.db.execute(stmt)
        return result.scalars().first()

    async def get_user_by_telegram(self, workspace_id: int, telegram_username: str) -> User | None:
        """Get user by Telegram username in workspace"""
        stmt = select(User).where(
            (User.workspace_id == workspace_id) &
            (User.telegram_username == telegram_username)
        )
        result = await self.db.execute(stmt)
        return result.scalars().first()

    async def get_user_by_slack(self, workspace_id: int, slack_user_id: str) -> User | None:
        """Get user by Slack user ID in workspace"""
        stmt = select(User).where(
            (User.workspace_id == workspace_id) &
            (User.slack_user_id == slack_user_id)
        )
        result = await self.db.execute(stmt)
        return result.scalars().first()

    async def get_all_users(self, workspace_id: int) -> list[User]:
        """Get all users in workspace"""
        stmt = select(User).where(User.workspace_id == workspace_id)
        result = await self.db.execute(stmt)
        return result.scalars().all()

    async def set_admin(self, user_id: int, is_admin: bool) -> User:
        """Set or unset admin status for a user"""
        user = await self.get_user(user_id)
        if user:
            user.is_admin = is_admin
            await self.db.commit()
            await self.db.refresh(user)
        return user

    async def get_all_admins(self, workspace_id: int) -> list[User]:
        """Get all admin users in workspace"""
        stmt = select(User).where(
            (User.workspace_id == workspace_id) &
            (User.is_admin == True)
        )
        result = await self.db.execute(stmt)
        return result.scalars().all()

    async def is_admin(self, user_id: int) -> bool:
        """Check if user is admin"""
        user = await self.get_user(user_id)
        return user.is_admin if user else False
