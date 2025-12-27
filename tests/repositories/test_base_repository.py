import pytest
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from app.repositories.base_repository import BaseRepository
from app.models import User, Workspace


class TestBaseRepository:
    """Test BaseRepository generic CRUD operations"""

    @pytest.fixture
    async def user_repo(self, db_session: AsyncSession):
        """Create a user repository instance"""
        repo = BaseRepository(db_session, User)
        # Create a workspace first
        workspace = Workspace(
            name="Test Workspace",
            workspace_type="telegram",
            external_id="123456789"
        )
        db_session.add(workspace)
        await db_session.commit()
        await db_session.refresh(workspace)
        return repo, workspace

    @pytest.mark.asyncio
    async def test_create_entity(self, user_repo, db_session: AsyncSession):
        """Test creating an entity"""
        repo, workspace = user_repo
        user_data = {
            "workspace_id": workspace.id,
            "telegram_username": "testuser",
            "first_name": "Test",
            "last_name": "User",
            "display_name": "Test User"
        }
        user = await repo.create(user_data)
        assert user.id is not None
        assert user.telegram_username == "testuser"
        assert user.workspace_id == workspace.id

    @pytest.mark.asyncio
    async def test_get_by_id(self, user_repo, db_session: AsyncSession):
        """Test getting entity by ID"""
        repo, workspace = user_repo
        # Create a user
        user_data = {
            "workspace_id": workspace.id,
            "telegram_username": "gettest",
            "first_name": "Get",
            "last_name": "Test"
        }
        created_user = await repo.create(user_data)

        # Get the user by ID
        retrieved_user = await repo.get_by_id(created_user.id)
        assert retrieved_user is not None
        assert retrieved_user.id == created_user.id
        assert retrieved_user.telegram_username == "gettest"

    @pytest.mark.asyncio
    async def test_get_by_id_not_found(self, user_repo):
        """Test getting non-existent entity"""
        repo, _ = user_repo
        user = await repo.get_by_id(9999)
        assert user is None

    @pytest.mark.asyncio
    async def test_list_all(self, user_repo, db_session: AsyncSession):
        """Test listing all entities"""
        repo, workspace = user_repo
        # Create multiple users
        for i in range(5):
            user_data = {
                "workspace_id": workspace.id,
                "telegram_username": f"user{i}",
                "first_name": f"User{i}",
                "last_name": "Test"
            }
            await repo.create(user_data)

        # List all users
        users = await repo.list_all(skip=0, limit=100)
        assert len(users) >= 5

    @pytest.mark.asyncio
    async def test_list_all_with_pagination(self, user_repo, db_session: AsyncSession):
        """Test pagination in list_all"""
        repo, workspace = user_repo
        # Create 10 users
        for i in range(10):
            user_data = {
                "workspace_id": workspace.id,
                "telegram_username": f"paginated{i}",
                "first_name": f"User{i}"
            }
            await repo.create(user_data)

        # Test pagination
        first_page = await repo.list_all(skip=0, limit=3)
        second_page = await repo.list_all(skip=3, limit=3)

        assert len(first_page) == 3
        assert len(second_page) == 3
        assert first_page[0].id != second_page[0].id

    @pytest.mark.asyncio
    async def test_update_entity(self, user_repo, db_session: AsyncSession):
        """Test updating an entity"""
        repo, workspace = user_repo
        # Create a user
        user_data = {
            "workspace_id": workspace.id,
            "telegram_username": "updateme",
            "first_name": "Update",
            "last_name": "Me"
        }
        user = await repo.create(user_data)

        # Update the user
        update_data = {
            "first_name": "Updated",
            "last_name": "Name",
            "is_admin": True
        }
        updated_user = await repo.update(user.id, update_data)
        assert updated_user is not None
        assert updated_user.first_name == "Updated"
        assert updated_user.last_name == "Name"
        assert updated_user.is_admin is True

    @pytest.mark.asyncio
    async def test_update_nonexistent_entity(self, user_repo):
        """Test updating non-existent entity"""
        repo, _ = user_repo
        result = await repo.update(9999, {"first_name": "None"})
        assert result is None

    @pytest.mark.asyncio
    async def test_delete_entity(self, user_repo, db_session: AsyncSession):
        """Test deleting an entity"""
        repo, workspace = user_repo
        # Create a user
        user_data = {
            "workspace_id": workspace.id,
            "telegram_username": "deleteme",
            "first_name": "Delete",
            "last_name": "Me"
        }
        user = await repo.create(user_data)
        user_id = user.id

        # Delete the user
        success = await repo.delete(user_id)
        assert success is True

        # Verify user is deleted
        deleted_user = await repo.get_by_id(user_id)
        assert deleted_user is None

    @pytest.mark.asyncio
    async def test_delete_nonexistent_entity(self, user_repo):
        """Test deleting non-existent entity"""
        repo, _ = user_repo
        success = await repo.delete(9999)
        assert success is False

    @pytest.mark.asyncio
    async def test_execute_raw_statement(self, user_repo, db_session: AsyncSession):
        """Test executing raw SQLAlchemy statements"""
        repo, workspace = user_repo
        from sqlalchemy import select

        # Create a user
        user_data = {
            "workspace_id": workspace.id,
            "telegram_username": "rawstmt",
            "first_name": "Raw",
            "last_name": "Statement"
        }
        await repo.create(user_data)

        # Execute raw statement
        stmt = select(User).where(
            User.telegram_username == "rawstmt",
            User.workspace_id == workspace.id
        )
        user = await repo.execute(stmt)
        assert user is not None
