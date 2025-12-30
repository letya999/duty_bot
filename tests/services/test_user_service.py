import pytest
from sqlalchemy.ext.asyncio import AsyncSession
from app.services.user_service import UserService
from app.repositories.user_repository import UserRepository
from app.models import Workspace, User, Team


class TestUserService:
    """Test UserService methods"""



    @pytest.fixture
    async def setup_user_service(self, db_session: AsyncSession):
        """Setup user service with test data"""
        workspace = Workspace(
            name="Test Workspace",
            workspace_type="telegram",
            external_id="123456789"
        )
        db_session.add(workspace)
        await db_session.commit()
        await db_session.refresh(workspace)

        user_repo = UserRepository(db_session)
        from app.repositories import UserAccountRepository
        user_account_repo = UserAccountRepository(db_session)
        service = UserService(user_repo, user_account_repo=user_account_repo)

        return service, workspace

    @pytest.mark.asyncio
    async def test_create_user(self, setup_user_service):
        """Test creating a user"""
        service, workspace = setup_user_service
        # Need to import UserAccount to query it
        from app.models import UserAccount
        from sqlalchemy import select

        user = await service.create_user(
            workspace_id=workspace.id,
            username="newuser",
            telegram_username="newuser",
            first_name="New",
            last_name="User",
            telegram_id=123456789
        )

        assert user.id is not None
        # Check UserAccount creation
        stmt = select(UserAccount).where(UserAccount.user_id == user.id)
        result = await service.user_repo.db.execute(stmt)
        accounts = result.scalars().all()
        assert len(accounts) > 0
        tg_acc = next((a for a in accounts if a.provider == 'telegram'), None)
        assert tg_acc is not None
        assert tg_acc.username == "newuser"
        assert tg_acc.provider_id == "123456789"

    @pytest.mark.asyncio
    async def test_get_user_by_id(self, setup_user_service):
        """Test getting user by ID"""
        service, workspace = setup_user_service

        user = await service.create_user(
            workspace_id=workspace.id,
            username="getuser",
            telegram_username="getuser",
            first_name="Get"
        )

        retrieved = await service.get_user(user.id)
        assert retrieved is not None
        # Verify it resembles the user we created
        assert retrieved.username == user.username

    @pytest.mark.asyncio
    async def test_get_user_by_telegram_username(self, setup_user_service):
        """Test getting user by Telegram username"""
        service, workspace = setup_user_service

        await service.create_user(
            workspace_id=workspace.id,
            username="tguser",
            telegram_username="tguser",
            first_name="TG"
        )

        user = await service.get_user_by_telegram(
            workspace.id,
            "tguser"
        )
        assert user is not None
        # We can't check specific user attributes easily without fetching account info, 
        # but finding the user implies success.
        assert user.username == "tguser" 


    @pytest.mark.asyncio
    async def test_update_user(self, setup_user_service):
        """Test updating user - via repository"""
        service, workspace = setup_user_service

        user = await service.create_user(
            workspace_id=workspace.id,
            username="updateuser",
            telegram_username="updateuser",
            first_name="Update"
        )

        # Update via repository since service doesn't have update method
        updated = await service.user_repo.update(
            user.id,
            {"first_name": "Updated", "last_name": "Name"}
        )

        assert updated.first_name == "Updated"
        assert updated.last_name == "Name"

    @pytest.mark.asyncio
    async def test_set_admin_status(self, setup_user_service):
        """Test setting admin status via repository"""
        service, workspace = setup_user_service

        user = await service.create_user(
            workspace_id=workspace.id,
            username="admin",
            telegram_username="admin",
            first_name="Admin"
        )

        # Make admin
        admin_user = await service.user_repo.update_admin_status(user.id, True)
        assert admin_user.is_admin is True

        # Remove admin
        regular_user = await service.user_repo.update_admin_status(user.id, False)
        assert regular_user.is_admin is False

    @pytest.mark.asyncio
    async def test_list_users_in_workspace(self, setup_user_service):
        """Test listing users in workspace"""
        service, workspace = setup_user_service

        # Create multiple users
        for i in range(3):
            await service.create_user(
                workspace_id=workspace.id,
                username=f"user{i}",
                telegram_username=f"user{i}",
                first_name=f"User{i}"
            )

        users = await service.user_repo.list_by_workspace(workspace.id)
        assert len(users) >= 3

    @pytest.mark.asyncio
    async def test_list_admins_in_workspace(self, setup_user_service):
        """Test listing admins in workspace"""
        service, workspace = setup_user_service

        # Create regular user
        await service.create_user(
            workspace_id=workspace.id,
            username="regular",
            telegram_username="regular",
            first_name="Regular"
        )

        # Create admin user
        admin = await service.create_user(
            workspace_id=workspace.id,
            username="admin",
            telegram_username="admin",
            first_name="Admin"
        )
        await service.user_repo.update_admin_status(admin.id, True)

        admins = await service.user_repo.list_admins_in_workspace(workspace.id)
        assert len(admins) >= 1
        assert all(a.is_admin for a in admins)

    @pytest.mark.asyncio
    async def test_merge_users(self, setup_user_service):
        """Test merging users preserves accounts"""
        from app.models import UserAccount
        from sqlalchemy import select
        service, workspace = setup_user_service

        # Create source user (Telegram)
        source = await service.create_user(
            workspace_id=workspace.id,
            username="source",
            telegram_username="source_tg",
            telegram_id=111111,
            first_name="Source"
        )

        # Create target user (Slack)
        target = await service.create_user(
            workspace_id=workspace.id,
            username="target",
            slack_user_id="U222222",
            first_name="Target"
        )

        # Verify initial state
        # Source has 1 account (Telegram)
        # We need to refresh/query properly as create_user might not expire session
        stmt = select(UserAccount).where(UserAccount.user_id == source.id)
        source_accounts = (await service.user_repo.db.execute(stmt)).scalars().all()
        assert len(source_accounts) == 1
        assert source_accounts[0].provider == 'telegram'

        # Target has 1 account (Slack)
        stmt = select(UserAccount).where(UserAccount.user_id == target.id)
        target_accounts = (await service.user_repo.db.execute(stmt)).scalars().all()
        assert len(target_accounts) == 1
        assert target_accounts[0].provider == 'slack'

        # Merge
        await service.merge_users(target.id, source.id)

        # Verify final state
        # Target should have 2 accounts
        stmt = select(UserAccount).where(UserAccount.user_id == target.id)
        result = await service.user_repo.db.execute(stmt)
        final_accounts = result.scalars().all()
        
        assert len(final_accounts) == 2
        providers = {acc.provider for acc in final_accounts}
        assert 'telegram' in providers
        assert 'slack' in providers
        
        # Source should be deleted
        source_check = await service.user_repo.get_by_id(source.id)
        assert source_check is None
