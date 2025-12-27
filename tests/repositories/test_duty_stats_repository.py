import pytest
from sqlalchemy.ext.asyncio import AsyncSession
from app.repositories.duty_stats_repository import DutyStatsRepository
from app.models import Workspace, Team, User, DutyStats


class TestDutyStatsRepository:
    """Test DutyStatsRepository methods"""

    @pytest.fixture
    async def setup_stats_repo(self, db_session: AsyncSession):
        """Setup stats repository with test data"""
        workspace = Workspace(
            name="Test Workspace",
            workspace_type="telegram",
            external_id="123456789"
        )
        db_session.add(workspace)
        await db_session.commit()
        await db_session.refresh(workspace)

        team = Team(
            workspace_id=workspace.id,
            name="backend",
            display_name="Backend Team"
        )
        db_session.add(team)
        await db_session.commit()
        await db_session.refresh(team)

        user = User(
            workspace_id=workspace.id,
            telegram_username="user1",
            first_name="User"
        )
        db_session.add(user)
        await db_session.commit()
        await db_session.refresh(user)

        repo = DutyStatsRepository(db_session)
        return repo, workspace, team, user

    @pytest.mark.asyncio
    async def test_create_stats(self, setup_stats_repo):
        """Test creating duty stats"""
        repo, workspace, team, user = setup_stats_repo

        stats = await repo.create({
            "workspace_id": workspace.id,
            "team_id": team.id,
            "user_id": user.id,
            "year": 2024,
            "month": 1,
            "duty_days": 10,
            "shift_days": 5
        })

        assert stats.id is not None
        assert stats.year == 2024
        assert stats.month == 1
        assert stats.duty_days == 10

    @pytest.mark.asyncio
    async def test_get_stats_by_id(self, setup_stats_repo):
        """Test getting stats by ID"""
        repo, workspace, team, user = setup_stats_repo

        stats = await repo.create({
            "workspace_id": workspace.id,
            "team_id": team.id,
            "user_id": user.id,
            "year": 2024,
            "month": 1,
            "duty_days": 10
        })

        retrieved = await repo.get_by_id(stats.id)
        assert retrieved is not None
        assert retrieved.duty_days == 10

    @pytest.mark.asyncio
    async def test_update_stats(self, setup_stats_repo):
        """Test updating stats"""
        repo, workspace, team, user = setup_stats_repo

        stats = await repo.create({
            "workspace_id": workspace.id,
            "team_id": team.id,
            "user_id": user.id,
            "year": 2024,
            "month": 1,
            "duty_days": 10
        })

        updated = await repo.update(stats.id, {"duty_days": 20})
        assert updated.duty_days == 20

    @pytest.mark.asyncio
    async def test_list_all_stats(self, setup_stats_repo):
        """Test listing all stats"""
        repo, workspace, team, user = setup_stats_repo

        # Create stats for multiple months
        for month in range(1, 4):
            await repo.create({
                "workspace_id": workspace.id,
                "team_id": team.id,
                "user_id": user.id,
                "year": 2024,
                "month": month,
                "duty_days": 10 + month
            })

        stats_list = await repo.list_all()
        assert len(stats_list) >= 3
