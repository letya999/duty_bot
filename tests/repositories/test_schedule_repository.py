import pytest
from datetime import date, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from app.repositories.schedule_repository import ScheduleRepository
from app.models import Workspace, User, Team, Schedule


class TestScheduleRepository:
    """Test ScheduleRepository methods"""

    @pytest.fixture
    async def setup_schedule_repo(self, db_session: AsyncSession):
        """Setup schedule repository with test data"""
        # Create workspace
        workspace = Workspace(
            name="Test Workspace",
            workspace_type="telegram",
            external_id="123456789"
        )
        db_session.add(workspace)
        await db_session.commit()
        await db_session.refresh(workspace)

        # Create team
        team = Team(
            workspace_id=workspace.id,
            name="backend",
            display_name="Backend Team"
        )
        db_session.add(team)
        await db_session.commit()
        await db_session.refresh(team)

        # Create users
        user1 = User(
            workspace_id=workspace.id,
            telegram_username="user1",
            first_name="User",
            last_name="One"
        )
        user2 = User(
            workspace_id=workspace.id,
            telegram_username="user2",
            first_name="User",
            last_name="Two"
        )
        db_session.add(user1)
        db_session.add(user2)
        await db_session.commit()
        await db_session.refresh(user1)
        await db_session.refresh(user2)

        repo = ScheduleRepository(db_session)
        return repo, workspace, team, user1, user2

    @pytest.mark.asyncio
    async def test_get_by_team_and_date(self, setup_schedule_repo):
        """Test getting schedule by team and date"""
        repo, workspace, team, user1, user2 = setup_schedule_repo

        test_date = date(2024, 1, 15)
        schedule = Schedule(
            team_id=team.id,
            user_id=user1.id,
            date=test_date
        )
        repo.db.add(schedule)
        await repo.db.commit()

        # Get schedule
        found = await repo.get_by_team_and_date(team.id, test_date)
        assert found is not None
        assert found.user_id == user1.id
        assert found.date == test_date

    @pytest.mark.asyncio
    async def test_get_by_team_and_date_not_found(self, setup_schedule_repo):
        """Test not finding schedule"""
        repo, workspace, team, user1, user2 = setup_schedule_repo

        found = await repo.get_by_team_and_date(team.id, date(2024, 1, 15))
        assert found is None

    @pytest.mark.asyncio
    async def test_list_by_team_and_date_range(self, setup_schedule_repo):
        """Test listing schedules by team and date range"""
        repo, workspace, team, user1, user2 = setup_schedule_repo

        start_date = date(2024, 1, 1)
        # Create schedules for a week
        for i in range(7):
            schedule = Schedule(
                team_id=team.id,
                user_id=user1.id if i % 2 == 0 else user2.id,
                date=start_date + timedelta(days=i)
            )
            repo.db.add(schedule)
        await repo.db.commit()

        # List schedules for week
        schedules = await repo.list_by_team_and_date_range(
            team.id,
            start_date,
            start_date + timedelta(days=6)
        )
        assert len(schedules) == 7
        assert all(s.team_id == team.id for s in schedules)

    @pytest.mark.asyncio
    async def test_list_by_team_and_date_range_empty(self, setup_schedule_repo):
        """Test empty result for date range with no schedules"""
        repo, workspace, team, user1, user2 = setup_schedule_repo

        schedules = await repo.list_by_team_and_date_range(
            team.id,
            date(2024, 1, 1),
            date(2024, 1, 31)
        )
        assert len(schedules) == 0

    @pytest.mark.asyncio
    async def test_list_by_user_and_date_range(self, setup_schedule_repo, db_session: AsyncSession):
        """Test listing schedules by user and date range"""
        repo, workspace, team, user1, user2 = setup_schedule_repo

        # Create another team
        team2 = Team(
            workspace_id=workspace.id,
            name="frontend",
            display_name="Frontend Team"
        )
        db_session.add(team2)
        await db_session.commit()
        await db_session.refresh(team2)

        start_date = date(2024, 1, 1)
        # Add user1 to both teams for the week
        for i in range(7):
            # Team 1 schedules
            schedule1 = Schedule(
                team_id=team.id,
                user_id=user1.id,
                date=start_date + timedelta(days=i)
            )
            # Team 2 schedules
            schedule2 = Schedule(
                team_id=team2.id,
                user_id=user1.id,
                date=start_date + timedelta(days=i)
            )
            repo.db.add(schedule1)
            repo.db.add(schedule2)
        await repo.db.commit()

        # List user's schedules across all teams
        schedules = await repo.list_by_user_and_date_range(
            user1.id,
            start_date,
            start_date + timedelta(days=6)
        )
        assert len(schedules) == 14  # 7 days * 2 teams
        assert all(s.user_id == user1.id for s in schedules)

    @pytest.mark.asyncio
    async def test_list_by_date(self, setup_schedule_repo, db_session: AsyncSession):
        """Test listing all schedules for a specific date"""
        repo, workspace, team, user1, user2 = setup_schedule_repo

        # Create another team
        team2 = Team(
            workspace_id=workspace.id,
            name="frontend",
            display_name="Frontend Team"
        )
        db_session.add(team2)
        await db_session.commit()
        await db_session.refresh(team2)

        test_date = date(2024, 1, 15)
        # Create schedules for different teams on same date
        schedule1 = Schedule(team_id=team.id, user_id=user1.id, date=test_date)
        schedule2 = Schedule(team_id=team2.id, user_id=user2.id, date=test_date)

        repo.db.add(schedule1)
        repo.db.add(schedule2)
        await repo.db.commit()

        # List all schedules for date
        schedules = await repo.list_by_date(test_date)
        # Should have at least 2
        date_schedules = [s for s in schedules if s.date == test_date]
        assert len(date_schedules) >= 2

    @pytest.mark.asyncio
    async def test_delete_by_team_and_date(self, setup_schedule_repo):
        """Test deleting schedule by team and date"""
        repo, workspace, team, user1, user2 = setup_schedule_repo

        test_date = date(2024, 1, 15)
        schedule = Schedule(
            team_id=team.id,
            user_id=user1.id,
            date=test_date
        )
        repo.db.add(schedule)
        await repo.db.commit()

        # Delete schedule
        success = await repo.delete_by_team_and_date(team.id, test_date)
        assert success is True

        # Verify it's deleted
        found = await repo.get_by_team_and_date(team.id, test_date)
        assert found is None

    @pytest.mark.asyncio
    async def test_delete_by_team_and_date_not_found(self, setup_schedule_repo):
        """Test delete returns False when not found"""
        repo, workspace, team, user1, user2 = setup_schedule_repo

        success = await repo.delete_by_team_and_date(
            team.id,
            date(2024, 1, 15)
        )
        assert success is False

    @pytest.mark.asyncio
    async def test_create_or_update_schedule_create(self, setup_schedule_repo):
        """Test creating schedule via create_or_update"""
        repo, workspace, team, user1, user2 = setup_schedule_repo

        test_date = date(2024, 1, 15)
        schedule = await repo.create_or_update_schedule(
            team.id,
            test_date,
            user1.id,
            is_shift=False
        )

        assert schedule.id is not None
        assert schedule.team_id == team.id
        assert schedule.user_id == user1.id
        assert schedule.date == test_date

    @pytest.mark.asyncio
    async def test_create_or_update_schedule_update(self, setup_schedule_repo):
        """Test updating schedule via create_or_update"""
        repo, workspace, team, user1, user2 = setup_schedule_repo

        test_date = date(2024, 1, 15)
        # Create initial schedule
        schedule1 = await repo.create_or_update_schedule(
            team.id,
            test_date,
            user1.id,
            is_shift=False
        )
        original_id = schedule1.id

        # Update with different user
        schedule2 = await repo.create_or_update_schedule(
            team.id,
            test_date,
            user2.id,
            is_shift=False
        )

        # Should be same schedule with updated user
        assert schedule2.id == original_id
        assert schedule2.user_id == user2.id

    @pytest.mark.asyncio
    async def test_create_or_update_schedule_shift_mode(self, setup_schedule_repo):
        """Test creating multiple shifts on same date"""
        repo, workspace, team, user1, user2 = setup_schedule_repo

        test_date = date(2024, 1, 15)
        # Create first shift
        schedule1 = await repo.create_or_update_schedule(
            team.id,
            test_date,
            user1.id,
            is_shift=True
        )

        # Create second shift for same date
        schedule2 = await repo.create_or_update_schedule(
            team.id,
            test_date,
            user2.id,
            is_shift=True
        )

        # Both should exist (different records)
        assert schedule1.id != schedule2.id
        assert schedule1.user_id == user1.id
        assert schedule2.user_id == user2.id

    @pytest.mark.asyncio
    async def test_create_or_update_schedule_deferred_commit(self, setup_schedule_repo):
        """Test deferred commit in create_or_update"""
        repo, workspace, team, user1, user2 = setup_schedule_repo

        test_date = date(2024, 1, 15)
        schedule = await repo.create_or_update_schedule(
            team.id,
            test_date,
            user1.id,
            is_shift=False,
            commit=False  # Deferred commit
        )

        # Schedule should have ID from flush
        assert schedule.id is not None
