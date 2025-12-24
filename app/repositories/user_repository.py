"""Repository for User model."""

from typing import Optional, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload
from app.models import User
from app.repositories.base_repository import BaseRepository


class UserRepository(BaseRepository[User]):
    """Repository for User operations."""

    def __init__(self, db: AsyncSession):
        super().__init__(db, User)

    async def get_by_telegram_username(self, workspace_id: int, telegram_username: str) -> Optional[User]:
        """Get user by Telegram username in workspace."""
        stmt = select(User).where(
            User.workspace_id == workspace_id,
            User.telegram_username == telegram_username
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_telegram_id(self, workspace_id: int, telegram_id: int) -> Optional[User]:
        """Get user by Telegram ID in workspace."""
        stmt = select(User).where(
            User.workspace_id == workspace_id,
            User.telegram_id == telegram_id
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_slack_user_id(self, workspace_id: int, slack_user_id: str) -> Optional[User]:
        """Get user by Slack user ID in workspace."""
        stmt = select(User).where(
            User.workspace_id == workspace_id,
            User.slack_user_id == slack_user_id
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_id_with_teams(self, user_id: int) -> Optional[User]:
        """Get user with loaded teams relationship."""
        stmt = select(User).where(User.id == user_id).options(selectinload(User.teams))
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def list_by_workspace(self, workspace_id: int, skip: int = 0, limit: int = 100) -> List[User]:
        """List all users in workspace."""
        stmt = select(User).where(User.workspace_id == workspace_id).offset(skip).limit(limit)
        result = await self.db.execute(stmt)
        return result.scalars().all()

    async def list_admins_in_workspace(self, workspace_id: int) -> List[User]:
        """List all admin users in workspace."""
        stmt = select(User).where(
            User.workspace_id == workspace_id,
            User.is_admin == True
        )
        result = await self.db.execute(stmt)
        return result.scalars().all()

    async def update_admin_status(self, user_id: int, is_admin: bool) -> Optional[User]:
        """Update user admin status."""
        user = await self.get_by_id(user_id)
        if user:
            user.is_admin = is_admin
            await self.db.commit()
            await self.db.refresh(user)
        return user
