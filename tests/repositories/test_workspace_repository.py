import pytest
from sqlalchemy.ext.asyncio import AsyncSession
from app.repositories.workspace_repository import WorkspaceRepository
from app.models import Workspace


class TestWorkspaceRepository:
    """Test WorkspaceRepository methods"""

    @pytest.fixture
    async def setup_workspace_repo(self, db_session: AsyncSession):
        """Setup workspace repository"""
        repo = WorkspaceRepository(db_session)
        return repo

    @pytest.mark.asyncio
    async def test_create_workspace(self, setup_workspace_repo):
        """Test creating workspace"""
        repo = setup_workspace_repo

        workspace = await repo.create({
            "name": "Test Workspace",
            "workspace_type": "telegram",
            "external_id": "123456789"
        })

        assert workspace.id is not None
        assert workspace.name == "Test Workspace"
        assert workspace.workspace_type == "telegram"

    @pytest.mark.asyncio
    async def test_get_by_id(self, setup_workspace_repo):
        """Test getting workspace by ID"""
        repo = setup_workspace_repo

        workspace = await repo.create({
            "name": "Test Workspace",
            "workspace_type": "telegram",
            "external_id": "123456789"
        })

        retrieved = await repo.get_by_id(workspace.id)
        assert retrieved is not None
        assert retrieved.name == "Test Workspace"

    @pytest.mark.asyncio
    async def test_get_by_external_id(self, setup_workspace_repo):
        """Test getting workspace by external ID"""
        repo = setup_workspace_repo

        workspace = await repo.create({
            "name": "Telegram Workspace",
            "workspace_type": "telegram",
            "external_id": "tg_123"
        })

        retrieved = await repo.get_by_external_id("telegram", "tg_123")
        assert retrieved is not None
        assert retrieved.workspace_type == "telegram"

    @pytest.mark.asyncio
    async def test_list_all_workspaces(self, setup_workspace_repo):
        """Test listing all workspaces"""
        repo = setup_workspace_repo

        # Create multiple workspaces
        for i in range(3):
            await repo.create({
                "name": f"Workspace {i}",
                "workspace_type": "telegram" if i % 2 == 0 else "slack",
                "external_id": f"id_{i}"
            })

        workspaces = await repo.list_all()
        assert len(workspaces) >= 3

    @pytest.mark.asyncio
    async def test_update_workspace(self, setup_workspace_repo):
        """Test updating workspace"""
        repo = setup_workspace_repo

        workspace = await repo.create({
            "name": "Original",
            "workspace_type": "telegram",
            "external_id": "123"
        })

        updated = await repo.update(workspace.id, {"name": "Updated"})
        assert updated.name == "Updated"

    @pytest.mark.asyncio
    async def test_delete_workspace(self, setup_workspace_repo):
        """Test deleting workspace"""
        repo = setup_workspace_repo

        workspace = await repo.create({
            "name": "To Delete",
            "workspace_type": "telegram",
            "external_id": "to_delete"
        })

        success = await repo.delete(workspace.id)
        assert success is True

        deleted = await repo.get_by_id(workspace.id)
        assert deleted is None

    @pytest.mark.asyncio
    async def test_unique_external_id(self, setup_workspace_repo, db_session: AsyncSession):
        """Test that external_id is unique per type"""
        repo = setup_workspace_repo

        # Create first workspace
        workspace1 = await repo.create({
            "name": "Workspace 1",
            "workspace_type": "telegram",
            "external_id": "same_id"
        })

        # Same external_id but different type should be allowed
        workspace2 = await repo.create({
            "name": "Workspace 2",
            "workspace_type": "slack",
            "external_id": "same_id"
        })

        assert workspace1.id != workspace2.id
        assert workspace1.workspace_type == "telegram"
        assert workspace2.workspace_type == "slack"
