import pytest
from unittest.mock import AsyncMock, MagicMock
from sqlalchemy.ext.asyncio import AsyncSession
from app.services.admin_service import AdminService
from app.models import Workspace, User, AdminLog
from app.repositories import AdminLogRepository, UserRepository


class TestAdminService:
    """Test AdminService methods"""

    @pytest.fixture
    async def setup_admin_service(self, db_session: AsyncSession):
        """Setup admin service with dependencies"""
        admin_log_repo = AdminLogRepository(db_session)
        user_repo = UserRepository(db_session)
        service = AdminService(admin_log_repo, user_repo)
        return service, admin_log_repo, user_repo, db_session

    @pytest.fixture
    async def workspace_with_users(self, db_session: AsyncSession):
        """Create workspace and users for testing"""
        workspace = Workspace(
            name="Test Workspace",
            workspace_type="telegram",
            external_id="123456789"
        )
        db_session.add(workspace)
        await db_session.flush()

        admin_user = User(
            workspace_id=workspace.id,
            username="admin",
            first_name="Admin",
            last_name="User",
            display_name="Admin User",
            is_admin=True
        )

        regular_user = User(
            workspace_id=workspace.id,
            username="regular",
            first_name="Regular",
            last_name="User",
            display_name="Regular User",
            is_admin=False
        )

        db_session.add_all([admin_user, regular_user])
        await db_session.flush()

        from app.models import UserAccount
        acc_admin = UserAccount(user_id=admin_user.id, workspace_id=workspace.id, provider="telegram", provider_id="111111", username="admin")
        acc_reg = UserAccount(user_id=regular_user.id, workspace_id=workspace.id, provider="telegram", provider_id="222222", username="regular")
        db_session.add(acc_admin)
        db_session.add(acc_reg)
        await db_session.commit()
        await db_session.refresh(admin_user)
        await db_session.refresh(regular_user)

        return workspace, admin_user, regular_user

    @pytest.mark.asyncio
    async def test_check_permission_admin_user(self, setup_admin_service, workspace_with_users):
        """Test permission check for admin user returns True"""
        service, _, _, _ = setup_admin_service
        workspace, admin_user, _ = workspace_with_users

        result = await service.check_permission(admin_user.id, workspace.id, "any_action")
        assert result is True

    @pytest.mark.asyncio
    async def test_check_permission_regular_user(self, setup_admin_service, workspace_with_users):
        """Test permission check for non-admin user returns False"""
        service, _, _, _ = setup_admin_service
        workspace, _, regular_user = workspace_with_users

        result = await service.check_permission(regular_user.id, workspace.id, "any_action")
        assert result is False

    @pytest.mark.asyncio
    async def test_check_permission_nonexistent_user(self, setup_admin_service, workspace_with_users):
        """Test permission check for non-existent user returns False"""
        service, _, _, _ = setup_admin_service
        workspace, _, _ = workspace_with_users

        result = await service.check_permission(99999, workspace.id, "any_action")
        assert result is False

    @pytest.mark.asyncio
    async def test_log_action(self, setup_admin_service, workspace_with_users):
        """Test logging admin action"""
        service, _, _, _ = setup_admin_service
        workspace, admin_user, regular_user = workspace_with_users

        log = await service.log_action(
            workspace_id=workspace.id,
            admin_id=admin_user.id,
            action="test_action",
            target_user_id=regular_user.id,
            details={"test": "data"}
        )

        assert log is not None
        assert log.workspace_id == workspace.id
        assert log.admin_user_id == admin_user.id
        assert log.action == "test_action"
        assert log.target_user_id == regular_user.id

    @pytest.mark.asyncio
    async def test_log_action_without_details(self, setup_admin_service, workspace_with_users):
        """Test logging action without details"""
        service, _, _, _ = setup_admin_service
        workspace, admin_user, _ = workspace_with_users

        log = await service.log_action(
            workspace_id=workspace.id,
            admin_id=admin_user.id,
            action="action_without_details"
        )

        assert log is not None
        assert log.workspace_id == workspace.id
        assert log.action == "action_without_details"

    @pytest.mark.asyncio
    async def test_log_action_without_target_user(self, setup_admin_service, workspace_with_users):
        """Test logging action without target user"""
        service, _, _, _ = setup_admin_service
        workspace, admin_user, _ = workspace_with_users

        log = await service.log_action(
            workspace_id=workspace.id,
            admin_id=admin_user.id,
            action="workspace_level_action",
            target_user_id=None
        )

        assert log is not None
        assert log.target_user_id is None

    @pytest.mark.asyncio
    async def test_get_action_history(self, setup_admin_service, workspace_with_users):
        """Test retrieving action history"""
        service, _, _, _ = setup_admin_service
        workspace, admin_user, _ = workspace_with_users

        # Create some logs
        await service.log_action(workspace.id, admin_user.id, "action1")
        await service.log_action(workspace.id, admin_user.id, "action2")
        await service.log_action(workspace.id, admin_user.id, "action3")

        history = await service.get_action_history(workspace.id, limit=100)

        assert len(history) >= 3
        assert all(log.workspace_id == workspace.id for log in history)

    @pytest.mark.asyncio
    async def test_get_action_history_with_limit(self, setup_admin_service, workspace_with_users):
        """Test action history respects limit"""
        service, _, _, _ = setup_admin_service
        workspace, admin_user, _ = workspace_with_users

        # Create multiple logs
        for i in range(10):
            await service.log_action(workspace.id, admin_user.id, f"action_{i}")

        history = await service.get_action_history(workspace.id, limit=5)

        assert len(history) <= 5

    @pytest.mark.asyncio
    async def test_get_user_action_history_as_admin(self, setup_admin_service, workspace_with_users):
        """Test getting action history where user is admin"""
        service, _, _, _ = setup_admin_service
        workspace, admin_user, regular_user = workspace_with_users

        await service.log_action(workspace.id, admin_user.id, "action1", regular_user.id)
        await service.log_action(workspace.id, admin_user.id, "action2", regular_user.id)

        history = await service.get_user_action_history(admin_user.id, workspace.id, limit=50)

        assert len(history) >= 2

    @pytest.mark.asyncio
    async def test_get_user_action_history_as_target(self, setup_admin_service, workspace_with_users):
        """Test getting action history where user is target"""
        service, _, _, _ = setup_admin_service
        workspace, admin_user, regular_user = workspace_with_users

        await service.log_action(workspace.id, admin_user.id, "action_on_user", regular_user.id)
        await service.log_action(workspace.id, admin_user.id, "another_action", regular_user.id)

        history = await service.get_user_action_history(regular_user.id, workspace.id, limit=50)

        assert len(history) >= 2

    @pytest.mark.asyncio
    async def test_get_user_action_history_sorting(self, setup_admin_service, workspace_with_users):
        """Test action history is sorted by timestamp in descending order"""
        service, _, _, _ = setup_admin_service
        workspace, admin_user, _ = workspace_with_users

        await service.log_action(workspace.id, admin_user.id, "action1")
        await service.log_action(workspace.id, admin_user.id, "action2")
        await service.log_action(workspace.id, admin_user.id, "action3")

        history = await service.get_user_action_history(admin_user.id, workspace.id, limit=50)

        # Check that timestamps are in descending order
        for i in range(len(history) - 1):
            assert history[i].timestamp >= history[i + 1].timestamp
