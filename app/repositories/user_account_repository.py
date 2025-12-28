"""Repository for UserAccount model."""

from typing import Optional, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from app.models import UserAccount
from app.repositories.base_repository import BaseRepository


class UserAccountRepository(BaseRepository[UserAccount]):
    """Repository for UserAccount operations."""

    def __init__(self, db: AsyncSession):
        super().__init__(db, UserAccount)

    async def get_by_provider_id(self, provider_id: str, workspace_id: Optional[int] = None) -> Optional[UserAccount]:
        """Get user account by provider ID and optional workspace ID."""
        stmt = select(UserAccount).where(UserAccount.provider_id == provider_id)
        if workspace_id:
            stmt = stmt.where(UserAccount.workspace_id == workspace_id)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_telegram_id(self, telegram_id: str, workspace_id: Optional[int] = None) -> Optional[UserAccount]:
        """Get user account by Telegram ID."""
        return await self.get_by_provider_id(telegram_id, workspace_id)

    async def get_by_slack_id(self, slack_user_id: str, workspace_id: Optional[int] = None) -> Optional[UserAccount]:
        """Get user account by Slack user ID."""
        return await self.get_by_provider_id(slack_user_id, workspace_id)

    async def list_by_user_id(self, user_id: int) -> List[UserAccount]:
        """List all accounts for a user."""
        stmt = select(UserAccount).where(UserAccount.user_id == user_id)
        result = await self.db.execute(stmt)
        return result.scalars().all()

    async def list_by_provider(self, provider: str) -> List[UserAccount]:
        """List all accounts for a specific provider."""
        stmt = select(UserAccount).where(UserAccount.provider == provider)
        result = await self.db.execute(stmt)
        return result.scalars().all()

    async def list_by_workspace(self, workspace_id: int) -> List[UserAccount]:
        """List all accounts in a workspace."""
        stmt = select(UserAccount).where(UserAccount.workspace_id == workspace_id)
        result = await self.db.execute(stmt)
        return result.scalars().all()

    async def get_by_username_and_provider(self, username: str, provider: str, workspace_id: Optional[int] = None) -> Optional[UserAccount]:
        """Get user account by username and provider."""
        stmt = select(UserAccount).where(
            UserAccount.username == username,
            UserAccount.provider == provider
        )
        if workspace_id:
            stmt = stmt.where(UserAccount.workspace_id == workspace_id)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def delete_by_id(self, account_id: int) -> bool:
        """Delete user account by ID."""
        account = await self.get_by_id(account_id)
        if not account:
            return False
        await self.db.delete(account)
        await self.db.commit()
        return True
