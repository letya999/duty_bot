"""
Authentication service handling OAuth flows and user provisioning.
"""

import logging
from typing import Optional, Dict, Any

from sqlalchemy import select, func, or_
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import User, UserAccount, Workspace
from app.config import get_settings
from app.repositories import (
    UserRepository,
    UserAccountRepository,
    WorkspaceRepository,
)
from app.services.user_account_service import UserAccountService

logger = logging.getLogger(__name__)
settings = get_settings()


class AuthService:
    """
    Service for OAuth authentication and user provisioning.

    Handles:
    - OAuth validation (Telegram, Slack)
    - User and workspace lookup/creation
    - Admin status verification
    - User data preparation
    """

    def __init__(
        self,
        user_repo: UserRepository,
        user_account_repo: UserAccountRepository,
        workspace_repo: WorkspaceRepository,
        db: AsyncSession,
    ):
        self.user_repo = user_repo
        self.user_account_repo = user_account_repo
        self.workspace_repo = workspace_repo
        self.db = db
        self.ua_service = UserAccountService(user_account_repo, user_repo, db)

    async def get_or_create_user_for_provider(
        self,
        provider: str,
        provider_id: str,
        user_info: Dict[str, Any],
        allow_registration: bool = True,
    ) -> tuple[Optional[User], Optional[Workspace]]:
        """
        Get or create user for OAuth provider (Telegram, Slack).

        Args:
            provider: 'telegram' or 'slack'
            provider_id: User ID from provider (string for consistency)
            user_info: User data from OAuth provider (must include relevant fields)
            allow_registration: Whether to create new users/workspaces

        Returns:
            Tuple of (User, Workspace) or (None, None) if user not found and registration disabled

        Raises:
            HTTPException: On validation errors
        """
        # Try to find existing user by provider ID across workspaces
        user, workspace = await self._find_existing_user(provider, provider_id)

        if user:
            logger.info(
                f"Found existing user {user.id} (provider: {provider}, "
                f"provider_id: {provider_id})"
            )
            return user, workspace

        if not allow_registration:
            logger.warning(
                f"User {provider_id} not found and registration is disabled"
            )
            return None, None

        # Create new workspace and user
        workspace, workspace_org_id = await self._get_or_create_workspace(provider, provider_id, user_info)

        # Try to find existing user by username or name in this workspace/organization
        # This handles cases where a user exists but hasn't linked this provider yet
        username = user_info.get("username")
        first_name = user_info.get("first_name")
        last_name = user_info.get("last_name")
        organization_id = workspace.organization_id or workspace_org_id

        # Try matching by username first
        if username:
            user = await self.find_user_by_username(provider, username, workspace.id, organization_id)
            if user:
                logger.info(
                    f"Found existing user {user.id} by username '{username}', "
                    f"linking {provider} account {provider_id}"
                )
                await self.ensure_user_account(
                    user_id=user.id,
                    provider=provider,
                    provider_id=provider_id,
                    workspace_id=workspace.id,
                    username=username,
                )
                # Refresh user to ensure relationships are loaded if needed
                await self.db.refresh(user)
                return user, workspace

        # Try matching by first_name + last_name if they don't match by username
        if first_name or last_name:
            user = await self.find_user_by_name(
                first_name, last_name, workspace.id, organization_id
            )
            if user:
                logger.info(
                    f"Found existing user {user.id} by name '{first_name} {last_name}', "
                    f"linking {provider} account {provider_id}"
                )
                await self.ensure_user_account(
                    user_id=user.id,
                    provider=provider,
                    provider_id=provider_id,
                    workspace_id=workspace.id,
                    username=username,
                )
                # Refresh user to ensure relationships are loaded if needed
                await self.db.refresh(user)
                return user, workspace

        user = await self._create_user_with_account(
            provider, provider_id, workspace.id, user_info, organization_id
        )

        return user, workspace

    async def _find_existing_user(
        self, provider: str, provider_id: str
    ) -> tuple[Optional[User], Optional[Workspace]]:
        """
        Find existing user by provider ID.

        Search strategy:
        1. Exact match: (provider, provider_id)
        2. Cross-provider match: provider_id only (user may have same ID in multiple platforms)

        This prevents creating duplicate users when the same provider_id is used
        across different platforms (e.g., user has same ID in both Telegram and Slack).
        """
        # First try: exact match by (provider, provider_id)
        stmt = (
            select(User)
            .join(UserAccount)
            .where(
                UserAccount.provider == provider,
                UserAccount.provider_id == provider_id,
            )
            .order_by(User.is_superadmin.desc(), User.is_admin.desc(), User.created_at.desc())
        )

        result = await self.db.execute(stmt)
        user = result.scalars().first()

        if user:
            logger.info(f"Found user {user.id} by exact match (provider={provider}, provider_id={provider_id})")
            workspace = await self.db.get(Workspace, user.workspace_id)
            return user, workspace

        # Second try: match by provider_id across ALL providers
        # Important: Some platforms may use the same ID for a user (e.g., user with
        # same U0930GD8F44 ID in both Telegram and Slack accounts)
        logger.debug(f"No exact match for (provider={provider}, provider_id={provider_id}), "
                     f"checking across all providers...")

        stmt = (
            select(User)
            .join(UserAccount)
            .where(UserAccount.provider_id == provider_id)
            .order_by(User.is_superadmin.desc(), User.is_admin.desc(), User.created_at.desc())
        )

        result = await self.db.execute(stmt)
        user = result.scalars().first()

        if user:
            logger.info(f"Found user {user.id} by cross-provider match (provider_id={provider_id} exists in {provider} context)")
            workspace = await self.db.get(Workspace, user.workspace_id)
            return user, workspace

        logger.debug(f"No existing user found for provider_id={provider_id}")
        return None, None

    async def find_user_by_username(
        self, provider: str, username: str, workspace_id: int, organization_id: Optional[int] = None
    ) -> Optional[User]:
        """Find user by username in specific workspace or organization.

        Search priority:
        1. Same workspace with matching username
        2. Same organization with matching username (if organization_id provided)
        """
        if not username:
            return None

        # First try to find in the same workspace
        stmt = (
            select(User)
            .where(
                func.lower(User.username) == username.lower(),
                User.workspace_id == workspace_id,
            )
        )
        result = await self.db.execute(stmt)
        user = result.scalars().first()

        if user:
            logger.info(f"Found user by username '{username}' in workspace {workspace_id}")
            return user

        # If not found in workspace and organization_id is available, try organization
        if organization_id:
            stmt = (
                select(User)
                .where(
                    func.lower(User.username) == username.lower(),
                    User.organization_id == organization_id,
                )
                .order_by(User.workspace_id.desc())  # Prefer users with workspace_id
            )
            result = await self.db.execute(stmt)
            user = result.scalars().first()

            if user:
                logger.info(f"Found user by username '{username}' in organization {organization_id}")
                return user

        logger.debug(f"User with username '{username}' not found in workspace {workspace_id} or organization {organization_id}")
        return None

    async def find_user_by_name(
        self, first_name: Optional[str], last_name: Optional[str],
        workspace_id: int, organization_id: Optional[int] = None
    ) -> Optional[User]:
        """Find user by first_name and last_name in workspace or organization.

        Search priority:
        1. Same workspace with matching name
        2. Same organization with matching name (if organization_id provided)
        """
        if not first_name and not last_name:
            return None

        # First try to find in the same workspace
        conditions = []
        if first_name:
            conditions.append(func.lower(User.first_name) == first_name.lower())
        if last_name:
            conditions.append(func.lower(User.last_name) == last_name.lower())

        stmt = (
            select(User)
            .where(User.workspace_id == workspace_id, *conditions)
        )
        result = await self.db.execute(stmt)
        user = result.scalars().first()

        if user:
            logger.info(f"Found user by name in workspace {workspace_id}: {first_name} {last_name}")
            return user

        # If not found in workspace and organization_id is available, try organization
        if organization_id:
            stmt = (
                select(User)
                .where(User.organization_id == organization_id, *conditions)
                .order_by(User.workspace_id.desc())  # Prefer users with workspace_id
            )
            result = await self.db.execute(stmt)
            user = result.scalars().first()

            if user:
                logger.info(f"Found user by name in organization {organization_id}: {first_name} {last_name}")
                return user

        logger.debug(f"User with name '{first_name} {last_name}' not found")
        return None

    async def _get_or_create_workspace(
        self, provider: str, provider_id: str, user_info: Dict[str, Any]
    ) -> tuple[Workspace, Optional[int]]:
        """Get or create workspace for OAuth provider.

        Returns:
            Tuple of (Workspace, organization_id) where organization_id may be None
        """
        workspace_type_map = {
            "telegram": "telegram",
            "slack": "slack",
        }

        workspace_type = workspace_type_map.get(provider, provider)

        stmt = select(Workspace).where(
            (Workspace.workspace_type == workspace_type)
            & (Workspace.external_id == provider_id)
        )

        if provider == "slack" and user_info.get("team_id"):
            stmt = select(Workspace).where(
                (Workspace.workspace_type == workspace_type)
                & (Workspace.external_id == user_info["team_id"])
            )

        result = await self.db.execute(stmt)
        workspace = result.scalars().first()

        if workspace:
            logger.info(f"Found existing workspace: {workspace.id} (org_id: {workspace.organization_id})")
            return workspace, workspace.organization_id

        # Create new workspace
        logger.info(f"Creating new workspace for {provider} user {provider_id}")

        # Get workspace name from provider-specific fields
        if provider == "slack":
            workspace_name = user_info.get("team_name", f"Workspace for {provider}")
        elif provider == "telegram":
            first_name = user_info.get("first_name", "User")
            workspace_name = f"Workspace for {first_name}"
        else:
            workspace_name = f"Workspace for {provider}"

        workspace = Workspace(
            workspace_type=workspace_type,
            external_id=provider_id,
            name=workspace_name,
        )

        self.db.add(workspace)
        await self.db.commit()
        await self.db.refresh(workspace)
        logger.info(f"Created workspace: {workspace.id}")

        return workspace, None

    async def _create_user_with_account(
        self,
        provider: str,
        provider_id: str,
        workspace_id: int,
        user_info: Dict[str, Any],
        organization_id: Optional[int] = None,
    ) -> User:
        """Create new user and associated UserAccount."""
        logger.info(f"Creating new user for {provider} ID {provider_id}")

        # Extract user info based on provider
        if provider == "telegram":
            first_name = user_info.get("first_name")
            last_name = user_info.get("last_name")
            username = user_info.get("username", str(provider_id))
            display_name = (
                f"{first_name or ''} {last_name or ''}".strip()
                or username
                or str(provider_id)
            )
        elif provider == "slack":
            first_name = user_info.get("first_name")
            last_name = user_info.get("last_name")
            username = user_info.get("username")
            display_name = (
                user_info.get("display_name")
                or user_info.get("real_name")
                or username
            )
        else:
            username = str(provider_id)
            first_name = user_info.get("first_name")
            last_name = user_info.get("last_name")
            display_name = (
                f"{first_name or ''} {last_name or ''}".strip() or username
            )

        # Create user
        user = User(
            workspace_id=workspace_id,
            organization_id=organization_id,
            username=username,
            first_name=first_name,
            last_name=last_name,
            display_name=display_name,
        )

        self.db.add(user)
        await self.db.commit()
        await self.db.refresh(user)

        # Create UserAccount
        user_account = UserAccount(
            user_id=user.id,
            workspace_id=workspace_id,
            provider=provider,
            provider_id=provider_id,
            username=username,
        )

        self.db.add(user_account)
        await self.db.commit()

        logger.info(f"Created user: {user.id} with {provider} account (org_id: {organization_id})")
        return user

    async def ensure_user_account(
        self,
        user_id: int,
        provider: str,
        provider_id: str,
        workspace_id: int,
        username: Optional[str] = None,
    ) -> None:
        """Ensure UserAccount exists, creating if necessary."""
        try:
            await self.ua_service.find_or_create_account(
                user_id=user_id,
                provider=provider,
                provider_id=provider_id,
                workspace_id=workspace_id,
                username=username,
            )
        except Exception as e:
            logger.warning(f"Failed to ensure UserAccount: {e}")

    def check_admin_status(self, user: User, provider: Optional[str] = None) -> bool:
        """
        Check if user is admin in their workspace or is a master admin.

        Checks:
        1. Local admin status in workspace
        2. Master admin IDs from settings (by provider or all providers)
        """
        if user.is_admin:
            return True

        if user.is_superadmin:
            return True

        # Check master admin IDs
        if provider == "telegram" and user.telegram_id:
            if str(user.telegram_id) in settings.get_admin_ids("telegram"):
                return True
        elif provider == "slack" and user.slack_user_id:
            if user.slack_user_id in settings.get_admin_ids("slack"):
                return True
        else:
            # Check both providers if no specific provider given
            if user.telegram_id and str(user.telegram_id) in settings.get_admin_ids(
                "telegram"
            ):
                return True
            if user.slack_user_id and user.slack_user_id in settings.get_admin_ids(
                "slack"
            ):
                return True

        return False

    def build_user_response(
        self, user: User, provider: Optional[str] = None
    ) -> Dict[str, Any]:
        """Build user data dict for API responses."""
        is_admin = self.check_admin_status(user, provider)

        return {
            "id": user.id,
            "username": user.username or user.telegram_username,
            "first_name": user.first_name,
            "last_name": user.last_name,
            "is_admin": is_admin,
            "is_superadmin": user.is_superadmin,
            "workspace_id": user.workspace_id,
        }
