import pytest
from datetime import date, timedelta
from unittest.mock import AsyncMock
from sqlalchemy.ext.asyncio import AsyncSession
from app.services.schedule_service import ScheduleService
from app.repositories.schedule_repository import ScheduleRepository
from app.repositories.team_repository import TeamRepository
from app.repositories.google_calendar_repository import GoogleCalendarRepository
from app.models import Workspace, User, Team, Schedule


class TestScheduleService:
    """Test ScheduleService business logic"""

    @pytest.fixture
    async def setup_schedule_service(self, db_session: AsyncSession):
        """Setup schedule service with test data"""
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
            display_name="Backend Team",
            has_shifts=False
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

        # Create service
        schedule_repo = ScheduleRepository(db_session)
        google_cal_repo = AsyncMock(spec=GoogleCalendarRepository)
        service = ScheduleService(schedule_repo, google_cal_repo)

        return service, workspace, team, user1, user2

    @pytest.mark.asyncio
    async def test_set_duty_future_date(self, setup_schedule_service):
        """Test setting duty for future date"""
        service, workspace, team, user1, user2 = setup_schedule_service

        future_date = date.today() + timedelta(days=1)
        schedule = await service.set_duty(
            team.id,
            user1.id,
            future_date
        )

        assert schedule.id is not None
        assert schedule.team_id == team.id
        assert schedule.user_id == user1.id
        assert schedule.date == future_date

    @pytest.mark.asyncio
    async def test_set_duty_past_date_blocked(self, setup_schedule_service):
        """Test that past dates are blocked by default"""
        service, workspace, team, user1, user2 = setup_schedule_service

        past_date = date.today() - timedelta(days=1)
        with pytest.raises(ValueError, match="Cannot schedule duty for past date"):
            await service.set_duty(team.id, user1.id, past_date)

    @pytest.mark.asyncio
    async def test_set_duty_past_date_forced(self, setup_schedule_service):
        """Test forcing past date with force flag"""
        service, workspace, team, user1, user2 = setup_schedule_service

        past_date = date.today() - timedelta(days=1)
        schedule = await service.set_duty(
            team.id,
            user1.id,
            past_date,
            force=True
        )

        assert schedule.date == past_date

    @pytest.mark.asyncio
    async def test_set_duty_invalid_team(self, setup_schedule_service):
        """Test setting duty for non-existent team"""
        service, workspace, team, user1, user2 = setup_schedule_service

        with pytest.raises(ValueError, match="Team .* not found"):
            await service.set_duty(9999, user1.id, date.today() + timedelta(days=1))

    @pytest.mark.asyncio
    async def test_set_duty_shift_without_shift_enabled(self, setup_schedule_service):
        """Test creating shift when shifts not enabled"""
        service, workspace, team, user1, user2 = setup_schedule_service

        future_date = date.today() + timedelta(days=1)
        with pytest.raises(ValueError, match="does not have shifts enabled"):
            await service.set_duty(
                team.id,
                user1.id,
                future_date,
                is_shift=True
            )

    @pytest.mark.asyncio
    async def test_set_duty_with_shifts_enabled(self, setup_schedule_service, db_session: AsyncSession):
        """Test creating shifts when enabled"""
        service, workspace, team, user1, user2 = setup_schedule_service

        # Enable shifts
        team.has_shifts = True
        await db_session.commit()

        future_date = date.today() + timedelta(days=1)
        schedule1 = await service.set_duty(
            team.id,
            user1.id,
            future_date,
            is_shift=True
        )
        schedule2 = await service.set_duty(
            team.id,
            user2.id,
            future_date,
            is_shift=True
        )

        assert schedule1.id != schedule2.id
        assert schedule1.user_id == user1.id
        assert schedule2.user_id == user2.id

    @pytest.mark.asyncio
    async def test_get_duty(self, setup_schedule_service):
        """Test getting duty for a date"""
        service, workspace, team, user1, user2 = setup_schedule_service

        future_date = date.today() + timedelta(days=1)
        created = await service.set_duty(team.id, user1.id, future_date)

        retrieved = await service.get_duty(team.id, future_date)
        assert retrieved is not None
        assert retrieved.id == created.id

    @pytest.mark.asyncio
    async def test_get_duties_by_date(self, setup_schedule_service):
        """Test getting all duties for a date"""
        service, workspace, team, user1, user2 = setup_schedule_service

        future_date = date.today() + timedelta(days=1)
        await service.set_duty(team.id, user1.id, future_date)

        duties = await service.get_duties_by_date(team.id, future_date)
        assert len(duties) >= 1
        assert any(d.user_id == user1.id for d in duties)

    @pytest.mark.asyncio
    async def test_get_duties_by_date_range(self, setup_schedule_service):
        """Test getting duties for date range"""
        service, workspace, team, user1, user2 = setup_schedule_service

        start_date = date.today() + timedelta(days=1)
        # Create duties for a week
        for i in range(7):
            await service.set_duty(
                team.id,
                user1.id if i % 2 == 0 else user2.id,
                start_date + timedelta(days=i)
            )

        duties = await service.get_duties_by_date_range(
            team.id,
            start_date,
            start_date + timedelta(days=6)
        )
        assert len(duties) == 7

    @pytest.mark.asyncio
    async def test_clear_duty(self, setup_schedule_service):
        """Test clearing a duty"""
        service, workspace, team, user1, user2 = setup_schedule_service

        future_date = date.today() + timedelta(days=1)
        await service.set_duty(team.id, user1.id, future_date)

        success = await service.clear_duty(team.id, future_date)
        assert success is True

        retrieved = await service.get_duty(team.id, future_date)
        assert retrieved is None

    @pytest.mark.asyncio
    async def test_get_today_duty(self, setup_schedule_service):
        """Test getting today's duty person"""
        service, workspace, team, user1, user2 = setup_schedule_service

        today = date.today()
        await service.set_duty(team.id, user1.id, today, force=True)

        user = await service.get_today_duty(team.id, today)
        assert user is not None
        assert user.id == user1.id

    @pytest.mark.asyncio
    async def test_check_user_schedule_conflict(self, setup_schedule_service):
        """Test checking for schedule conflicts"""
        service, workspace, team, user1, user2 = setup_schedule_service

        future_date = date.today() + timedelta(days=1)
        await service.set_duty(team.id, user1.id, future_date)

        # Check if user has conflict
        conflict = await service.check_user_schedule_conflict(user1.id, future_date)
        assert conflict is not None
        assert conflict["user_id"] == user1.id
        assert conflict["team_name"] == team.name

        # Check user without conflict
        conflict = await service.check_user_schedule_conflict(user2.id, future_date)
        assert conflict is None

    @pytest.mark.asyncio
    async def test_check_user_schedule_conflict_by_workspace(
        self,
        setup_schedule_service,
        db_session: AsyncSession
    ):
        """Test checking conflicts within workspace"""
        service, workspace, team, user1, user2 = setup_schedule_service

        # Create another workspace
        other_workspace = Workspace(
            name="Other Workspace",
            workspace_type="slack",
            external_id="slack123"
        )
        db_session.add(other_workspace)
        await db_session.commit()
        await db_session.refresh(other_workspace)

        future_date = date.today() + timedelta(days=1)
        await service.set_duty(team.id, user1.id, future_date)

        # Check conflict within workspace
        conflict = await service.check_user_schedule_conflict(
            user1.id,
            future_date,
            workspace.id
        )
        assert conflict is not None

    @pytest.mark.asyncio
    async def test_update_duty(self, setup_schedule_service):
        """Test updating an existing duty"""
        service, workspace, team, user1, user2 = setup_schedule_service

        future_date = date.today() + timedelta(days=1)
        schedule = await service.set_duty(team.id, user1.id, future_date)

        # Update duty
        new_date = future_date + timedelta(days=1)
        updated = await service.update_duty(
            schedule.id,
            user2.id,
            new_date,
            team.id
        )

        assert updated.id == schedule.id
        assert updated.user_id == user2.id
        assert updated.date == new_date
