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
        """Get user by Telegram username in workspace (case-insensitive) via UserAccount or User.username."""
        from app.models import UserAccount
        from sqlalchemy import func, or_, and_
        
        stmt = select(User).outerjoin(UserAccount).where(
            User.workspace_id == workspace_id,
            or_(
                func.lower(User.username) == telegram_username.lower(),
                and_(
                    UserAccount.provider == 'telegram',
                    func.lower(UserAccount.username) == telegram_username.lower()
                )
            )
        ).options(selectinload(User.user_accounts))
        
        result = await self.db.execute(stmt)
        return result.scalars().first()

    async def find_anywhere_by_telegram_username(self, telegram_username: str) -> Optional[User]:
        """Find user by Telegram username across all workspaces (case-insensitive) via UserAccount."""
        from app.models import UserAccount
        from sqlalchemy import func
        stmt = select(User).join(UserAccount).where(
            UserAccount.provider == 'telegram',
            func.lower(UserAccount.username) == telegram_username.lower()
        ).limit(1).options(selectinload(User.user_accounts))
        result = await self.db.execute(stmt)
        return result.scalars().first()

    async def get_by_telegram_id(self, workspace_id: int, telegram_id: int) -> Optional[User]:
        """Get user by Telegram ID in workspace via UserAccount."""
        from app.models import UserAccount
        stmt = select(User).join(UserAccount).where(
            User.workspace_id == workspace_id,
            UserAccount.provider == 'telegram',
            UserAccount.provider_id == str(telegram_id)
        ).options(selectinload(User.user_accounts))
        result = await self.db.execute(stmt)
        return result.scalars().first()

    async def get_by_username(self, workspace_id: int, username: str) -> Optional[User]:
        """Get user by username or messenger handle in workspace."""
        from app.models import UserAccount
        from sqlalchemy import func, or_, and_
        
        stmt = select(User).outerjoin(UserAccount).where(
            User.workspace_id == workspace_id,
            or_(
                func.lower(User.username) == username.lower(),
                func.lower(UserAccount.username) == username.lower()
            )
        ).options(selectinload(User.user_accounts))
        
        result = await self.db.execute(stmt)
        return result.scalars().first()

    async def get_by_email(self, workspace_id: int, email: str) -> Optional[User]:
        """Get user by email in workspace (via UserAccount)."""
        from app.models import UserAccount
        from sqlalchemy import func
        stmt = select(User).join(UserAccount).where(
            User.workspace_id == workspace_id,
            func.lower(UserAccount.account_email) == email.lower()
        ).options(selectinload(User.user_accounts))
        result = await self.db.execute(stmt)
        return result.scalars().first()

    async def get_by_slack_user_id(self, workspace_id: int, slack_user_id: str) -> Optional[User]:
        """Get user by Slack user ID in workspace via UserAccount."""
        from app.models import UserAccount
        stmt = select(User).join(UserAccount).where(
            User.workspace_id == workspace_id,
            UserAccount.provider == 'slack',
            UserAccount.provider_id == slack_user_id
        ).options(selectinload(User.user_accounts))
        result = await self.db.execute(stmt)
        return result.scalars().first()

    async def get_by_id(self, user_id: int) -> Optional[User]:
        """Get user by ID with user_accounts loaded."""
        stmt = select(User).where(User.id == user_id).options(selectinload(User.user_accounts))
        result = await self.db.execute(stmt)
        return result.scalars().first()

    async def get_by_id_with_teams(self, user_id: int) -> Optional[User]:
        """Get user with loaded teams relationship."""
        stmt = select(User).where(User.id == user_id).options(selectinload(User.teams), selectinload(User.user_accounts))
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def list_by_workspace(self, workspace_id: int, skip: int = 0, limit: int = 100) -> List[User]:
        """List all users in workspace (or shared organization)."""
        from app.models import Workspace
        from sqlalchemy import or_

        # Get organization_id for the workspace
        stmt_org = select(Workspace.organization_id).where(Workspace.id == workspace_id)
        result_org = await self.db.execute(stmt_org)
        organization_id = result_org.scalar_one_or_none()

        query = select(User).options(selectinload(User.user_accounts))

        if organization_id:
            # Join Workspace to check its organization_id
            query = query.join(Workspace).where(
                or_(
                    User.workspace_id == workspace_id,
                    Workspace.organization_id == organization_id,
                    User.organization_id == organization_id
                )
            )
        else:
            query = query.where(User.workspace_id == workspace_id)

        stmt = query.offset(skip).limit(limit)
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
        return user

    async def get_by_provider_id_in_org(self, organization_id: int, provider: str, provider_id: str) -> Optional[User]:
        """Get user by provider ID within the same organization."""
        from app.models import UserAccount
        stmt = select(User).join(UserAccount).where(
            User.organization_id == organization_id,
            UserAccount.provider == provider,
            UserAccount.provider_id == provider_id
        ).options(selectinload(User.user_accounts))
        result = await self.db.execute(stmt)
        return result.scalars().first()
