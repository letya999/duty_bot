import pytest
from sqlalchemy.ext.asyncio import AsyncSession
from app.repositories.user_repository import UserRepository
from app.models import User, Workspace, Team, team_members


class TestUserRepository:
    """Test UserRepository specialized methods"""

    @pytest.fixture
    async def setup_user_repo(self, db_session: AsyncSession):
        """Setup user repository with test data"""
        # Create workspace
        workspace = Workspace(
            name="Test Workspace",
            workspace_type="telegram",
            external_id="123456789"
        )
        db_session.add(workspace)
        await db_session.commit()
        await db_session.refresh(workspace)

        # Create repository
        repo = UserRepository(db_session)
        return repo, workspace

    @pytest.mark.asyncio
    async def test_get_by_telegram_username(self, setup_user_repo):
        """Test getting user by Telegram username"""
        repo, workspace = setup_user_repo

        # Create a user
        user = User(
            workspace_id=workspace.id,
            telegram_username="testuser",
            first_name="Test",
            last_name="User"
        )
        repo.db.add(user)
        await repo.db.commit()

        # Get user by username
        found_user = await repo.get_by_telegram_username(
            workspace.id, "testuser"
        )
        assert found_user is not None
        assert found_user.telegram_username == "testuser"

    @pytest.mark.asyncio
    async def test_get_by_telegram_username_case_insensitive(self, setup_user_repo):
        """Test case-insensitive Telegram username lookup"""
        repo, workspace = setup_user_repo

        user = User(
            workspace_id=workspace.id,
            telegram_username="CaseSensitive",
            first_name="Test"
        )
        repo.db.add(user)
        await repo.db.commit()

        # Try different cases
        found_user = await repo.get_by_telegram_username(
            workspace.id, "casesensitive"
        )
        assert found_user is not None
        assert found_user.telegram_username == "CaseSensitive"

    @pytest.mark.asyncio
    async def test_get_by_telegram_username_not_found(self, setup_user_repo):
        """Test not finding user by Telegram username"""
        repo, workspace = setup_user_repo
        user = await repo.get_by_telegram_username(
            workspace.id, "nonexistent"
        )
        assert user is None

    @pytest.mark.asyncio
    async def test_get_by_telegram_id(self, setup_user_repo):
        """Test getting user by Telegram ID"""
        repo, workspace = setup_user_repo

        user = User(
            workspace_id=workspace.id,
            telegram_id=123456789,
            first_name="Test"
        )
        repo.db.add(user)
        await repo.db.commit()

        found_user = await repo.get_by_telegram_id(
            workspace.id, 123456789
        )
        assert found_user is not None
        assert found_user.telegram_id == 123456789

    @pytest.mark.asyncio
    async def test_get_by_slack_user_id(self, setup_user_repo):
        """Test getting user by Slack user ID"""
        repo, workspace = setup_user_repo

        user = User(
            workspace_id=workspace.id,
            slack_user_id="U12345678",
            first_name="Test"
        )
        repo.db.add(user)
        await repo.db.commit()

        found_user = await repo.get_by_slack_user_id(
            workspace.id, "U12345678"
        )
        assert found_user is not None
        assert found_user.slack_user_id == "U12345678"

    @pytest.mark.asyncio
    async def test_list_by_workspace(self, setup_user_repo, db_session: AsyncSession):
        """Test listing users by workspace"""
        repo, workspace = setup_user_repo

        # Create users in this workspace
        for i in range(3):
            user = User(
                workspace_id=workspace.id,
                telegram_username=f"user{i}",
                first_name=f"User{i}"
            )
            repo.db.add(user)
        await repo.db.commit()

        # Create another workspace with its own user
        other_workspace = Workspace(
            name="Other Workspace",
            workspace_type="slack",
            external_id="other123"
        )
        db_session.add(other_workspace)
        await db_session.commit()
        await db_session.refresh(other_workspace)

        other_user = User(
            workspace_id=other_workspace.id,
            telegram_username="otheruser",
            first_name="Other"
        )
        db_session.add(other_user)
        await db_session.commit()

        # List users in first workspace
        users = await repo.list_by_workspace(workspace.id)
        assert len(users) >= 3
        assert all(u.workspace_id == workspace.id for u in users)

    @pytest.mark.asyncio
    async def test_list_admins_in_workspace(self, setup_user_repo):
        """Test listing admin users in workspace"""
        repo, workspace = setup_user_repo

        # Create mix of admin and non-admin users
        admin_user = User(
            workspace_id=workspace.id,
            telegram_username="admin1",
            first_name="Admin",
            is_admin=True
        )
        repo.db.add(admin_user)

        regular_user = User(
            workspace_id=workspace.id,
            telegram_username="regular1",
            first_name="Regular",
            is_admin=False
        )
        repo.db.add(regular_user)
        await repo.db.commit()

        # List admins
        admins = await repo.list_admins_in_workspace(workspace.id)
        assert len(admins) >= 1
        assert all(u.is_admin for u in admins)

    @pytest.mark.asyncio
    async def test_update_admin_status(self, setup_user_repo):
        """Test updating user admin status"""
        repo, workspace = setup_user_repo

        user = User(
            workspace_id=workspace.id,
            telegram_username="admintest",
            first_name="Test",
            is_admin=False
        )
        repo.db.add(user)
        await repo.db.commit()
        await repo.db.refresh(user)
        user_id = user.id

        # Make user admin
        updated_user = await repo.update_admin_status(user_id, True)
        assert updated_user.is_admin is True

        # Remove admin
        updated_user = await repo.update_admin_status(user_id, False)
        assert updated_user.is_admin is False

    @pytest.mark.asyncio
    async def test_get_by_id_with_teams(self, setup_user_repo):
        """Test getting user with loaded teams"""
        repo, workspace = setup_user_repo

        # Create user and teams
        user = User(
            workspace_id=workspace.id,
            telegram_username="teamuser",
            first_name="Team",
            last_name="User"
        )
        repo.db.add(user)
        await repo.db.commit()
        await repo.db.refresh(user)

        # Get user with teams relationship loaded
        user_with_teams = await repo.get_by_id_with_teams(user.id)
        assert user_with_teams is not None
        assert user_with_teams.telegram_username == "teamuser"

    @pytest.mark.asyncio
    async def test_workspace_isolation(self, setup_user_repo, db_session: AsyncSession):
        """Test that users are isolated by workspace"""
        repo, workspace1 = setup_user_repo

        # Create user in workspace 1
        user1 = User(
            workspace_id=workspace1.id,
            telegram_username="samename",
            first_name="User"
        )
        repo.db.add(user1)
        await repo.db.commit()

        # Create different workspace
        workspace2 = Workspace(
            name="Workspace 2",
            workspace_type="slack",
            external_id="slack123"
        )
        db_session.add(workspace2)
        await db_session.commit()

        # Create user with same username in workspace 2
        user2 = User(
            workspace_id=workspace2.id,
            telegram_username="samename",
            first_name="User"
        )
        db_session.add(user2)
        await db_session.commit()

        # Get by username should only return user from requested workspace
        found = await repo.get_by_telegram_username(workspace1.id, "samename")
        assert found.workspace_id == workspace1.id
