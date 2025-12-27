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
        service = UserService(user_repo)

        return service, workspace

    @pytest.mark.asyncio
    async def test_create_user(self, setup_user_service):
        """Test creating a user"""
        service, workspace = setup_user_service

        user = await service.create_user(
            workspace_id=workspace.id,
            username="newuser",
            telegram_username="newuser",
            first_name="New",
            last_name="User",
            telegram_id=123456789
        )

        assert user.id is not None
        assert user.telegram_username == "newuser"
        assert user.telegram_id == 123456789

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
        assert retrieved.telegram_username == "getuser"

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
        assert user.telegram_username == "tguser"

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
