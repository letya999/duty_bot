"""Service for UserAccount operations."""

from typing import Optional, List
from sqlalchemy.ext.asyncio import AsyncSession
from app.models import UserAccount, User
from app.repositories import UserAccountRepository, UserRepository
from app.exceptions import NotFoundError, ConflictError


class UserAccountService:
    """Service for managing user accounts (login methods)."""

    def __init__(
        self,
        user_account_repo: UserAccountRepository,
        user_repo: UserRepository,
        db: AsyncSession
    ):
        self.user_account_repo = user_account_repo
        self.user_repo = user_repo
        self.db = db

    async def create_user_account(
        self,
        user_id: int,
        provider: str,
        provider_id: str,
        workspace_id: Optional[int] = None,
        username: Optional[str] = None,
        account_email: Optional[str] = None
    ) -> UserAccount:
        """Create a new user account (login method)."""
        # Verify user exists
        user = await self.user_repo.get_by_id(user_id)
        if not user:
            raise NotFoundError(f"User {user_id} not found")

        # Check if this provider_id already exists
        existing = await self.user_account_repo.get_by_provider_id(provider_id, workspace_id)
        if existing:
            raise ConflictError(f"Account with {provider} ID {provider_id} already exists")

        return await self.user_account_repo.create({
            'user_id': user_id,
            'provider': provider,
            'provider_id': provider_id,
            'workspace_id': workspace_id,
            'username': username,
            'account_email': account_email
        })

    async def get_user_account(self, account_id: int) -> Optional[UserAccount]:
        """Get user account by ID."""
        return await self.user_account_repo.get_by_id(account_id)

    async def list_user_accounts(self, user_id: int) -> List[UserAccount]:
        """List all accounts for a user."""
        return await self.user_account_repo.list_by_user_id(user_id)

    async def get_user_by_provider_id(
        self,
        provider: str,
        provider_id: str,
        workspace_id: Optional[int] = None
    ) -> Optional[User]:
        """Get user by provider ID (find user by login method)."""
        account = await self.user_account_repo.get_by_provider_id(provider_id, workspace_id)
        if not account:
            return None
        return await self.user_repo.get_by_id(account.user_id)

    async def update_user_account(
        self,
        account_id: int,
        username: Optional[str] = None,
        account_email: Optional[str] = None
    ) -> Optional[UserAccount]:
        """Update user account details."""
        account = await self.user_account_repo.get_by_id(account_id)
        if not account:
            raise NotFoundError(f"User account {account_id} not found")

        update_data = {}
        if username is not None:
            update_data['username'] = username
        if account_email is not None:
            update_data['account_email'] = account_email

        return await self.user_account_repo.update(account_id, update_data)

    async def delete_user_account(self, account_id: int) -> bool:
        """Delete a user account (remove login method)."""
        account = await self.user_account_repo.get_by_id(account_id)
        if not account:
            raise NotFoundError(f"User account {account_id} not found")

        # Check if this is the user's last account
        accounts = await self.user_account_repo.list_by_user_id(account.user_id)
        if len(accounts) <= 1:
            raise ConflictError("Cannot delete the last login method for a user")

        return await self.user_account_repo.delete(account_id)

    async def get_user_accounts_summary(self, user_id: int) -> dict:
        """Get summary of all login methods for a user."""
        accounts = await self.user_account_repo.list_by_user_id(user_id)
        summary = {
            'slack': [],
            'telegram': []
        }

        for account in accounts:
            account_info = {
                'id': account.id,
                'provider_id': account.provider_id,
                'username': account.username,
                'workspace_id': account.workspace_id,
                'email': account.account_email,
                'created_at': account.created_at
            }
            summary[account.provider].append(account_info)

        return summary

    async def find_or_create_account(
        self,
        user_id: int,
        provider: str,
        provider_id: str,
        workspace_id: Optional[int] = None,
        username: Optional[str] = None,
        account_email: Optional[str] = None
    ) -> UserAccount:
        """Get existing account or create new one."""
        existing = await self.user_account_repo.get_by_provider_id(provider_id, workspace_id)
        if existing:
            return existing

        return await self.create_user_account(
            user_id=user_id,
            provider=provider,
            provider_id=provider_id,
            workspace_id=workspace_id,
            username=username,
            account_email=account_email
        )
