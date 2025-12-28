import pytest
from datetime import date, timedelta
from unittest.mock import AsyncMock, MagicMock
from sqlalchemy.ext.asyncio import AsyncSession
from app.services.rotation_service import RotationService
from app.repositories.rotation_config_repository import RotationConfigRepository
from app.repositories.schedule_repository import ScheduleRepository
from app.repositories.user_repository import UserRepository
from app.models import Workspace, User, Team, RotationConfig


class TestRotationService:
    """Test RotationService business logic"""

    @pytest.fixture
    async def setup_rotation_service(self, db_session: AsyncSession):
        """Setup rotation service with test data"""
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
            last_name="One",
            display_name="User One"
        )
        user2 = User(
            workspace_id=workspace.id,
            telegram_username="user2",
            first_name="User",
            last_name="Two",
            display_name="User Two"
        )
        user3 = User(
            workspace_id=workspace.id,
            telegram_username="user3",
            first_name="User",
            last_name="Three",
            display_name="User Three"
        )
        db_session.add(user1)
        db_session.add(user2)
        db_session.add(user3)
        await db_session.commit()
        await db_session.refresh(user1)
        await db_session.refresh(user2)
        await db_session.refresh(user3)

        # Create repositories and service
        rotation_config_repo = RotationConfigRepository(db_session)
        schedule_repo = ScheduleRepository(db_session)
        user_repo = UserRepository(db_session)
        service = RotationService(rotation_config_repo, schedule_repo, user_repo)

        return service, workspace, team, user1, user2, user3

    @pytest.mark.asyncio
    async def test_enable_rotation(self, setup_rotation_service):
        """Test enabling rotation for a team"""
        service, workspace, team, user1, user2, user3 = setup_rotation_service

        member_ids = [user1.id, user2.id, user3.id]
        config = await service.enable_rotation(team, member_ids)

        assert config is not None
        assert config.team_id == team.id
        assert config.enabled is True
        assert config.member_ids == member_ids
        assert config.last_assigned_user_id == user1.id

    @pytest.mark.asyncio
    async def test_enable_rotation_updates_existing_config(self, setup_rotation_service, db_session: AsyncSession):
        """Test that enabling rotation updates existing config"""
        service, workspace, team, user1, user2, user3 = setup_rotation_service

        # Create initial config
        initial_config = RotationConfig(
            team_id=team.id,
            enabled=False,
            member_ids=[user1.id],
            last_assigned_user_id=None
        )
        db_session.add(initial_config)
        await db_session.commit()
        await db_session.refresh(initial_config)
        config_id = initial_config.id

        # Enable rotation with new members
        member_ids = [user1.id, user2.id, user3.id]
        config = await service.enable_rotation(team, member_ids)

        assert config.id == config_id  # Same config updated
        assert config.enabled is True
        assert config.member_ids == member_ids

    @pytest.mark.asyncio
    async def test_disable_rotation(self, setup_rotation_service, db_session: AsyncSession):
        """Test disabling rotation for a team"""
        service, workspace, team, user1, user2, user3 = setup_rotation_service

        # Create enabled rotation config
        config = RotationConfig(
            team_id=team.id,
            enabled=True,
            member_ids=[user1.id, user2.id]
        )
        db_session.add(config)
        await db_session.commit()

        # Disable rotation
        result = await service.disable_rotation(team)

        assert result is True

        # Verify it's disabled
        updated_config = await service.get_rotation_config(team)
        assert updated_config.enabled is False

    @pytest.mark.asyncio
    async def test_disable_rotation_no_config(self, setup_rotation_service):
        """Test disabling rotation when no config exists"""
        service, workspace, team, user1, user2, user3 = setup_rotation_service

        result = await service.disable_rotation(team)

        assert result is False

    @pytest.mark.asyncio
    async def test_get_rotation_config(self, setup_rotation_service, db_session: AsyncSession):
        """Test getting rotation config for a team"""
        service, workspace, team, user1, user2, user3 = setup_rotation_service

        # Create rotation config
        config = RotationConfig(
            team_id=team.id,
            enabled=True,
            member_ids=[user1.id, user2.id]
        )
        db_session.add(config)
        await db_session.commit()

        # Get config
        retrieved_config = await service.get_rotation_config(team)

        assert retrieved_config is not None
        assert retrieved_config.team_id == team.id
        assert retrieved_config.enabled is True

    @pytest.mark.asyncio
    async def test_get_rotation_config_none(self, setup_rotation_service):
        """Test getting rotation config when none exists"""
        service, workspace, team, user1, user2, user3 = setup_rotation_service

        config = await service.get_rotation_config(team)

        assert config is None

    @pytest.mark.asyncio
    async def test_get_next_person_first_assignment(self, setup_rotation_service, db_session: AsyncSession):
        """Test getting next person when no one has been assigned yet"""
        service, workspace, team, user1, user2, user3 = setup_rotation_service

        # Create rotation config with no last assigned user
        config = RotationConfig(
            team_id=team.id,
            enabled=True,
            member_ids=[user1.id, user2.id, user3.id],
            last_assigned_user_id=None
        )
        db_session.add(config)
        await db_session.commit()

        # Get next person
        next_person = await service.get_next_person(team, date.today())

        assert next_person is not None
        assert next_person.id == user1.id

    @pytest.mark.asyncio
    async def test_get_next_person_rotation(self, setup_rotation_service, db_session: AsyncSession):
        """Test getting next person in rotation sequence"""
        service, workspace, team, user1, user2, user3 = setup_rotation_service

        # Create rotation config with user1 as last assigned
        config = RotationConfig(
            team_id=team.id,
            enabled=True,
            member_ids=[user1.id, user2.id, user3.id],
            last_assigned_user_id=user1.id
        )
        db_session.add(config)
        await db_session.commit()

        # Get next person (should be user2)
        next_person = await service.get_next_person(team, date.today())

        assert next_person is not None
        assert next_person.id == user2.id

    @pytest.mark.asyncio
    async def test_get_next_person_wraps_around(self, setup_rotation_service, db_session: AsyncSession):
        """Test that rotation wraps around to first person"""
        service, workspace, team, user1, user2, user3 = setup_rotation_service

        # Create rotation config with user3 as last assigned (last in list)
        config = RotationConfig(
            team_id=team.id,
            enabled=True,
            member_ids=[user1.id, user2.id, user3.id],
            last_assigned_user_id=user3.id
        )
        db_session.add(config)
        await db_session.commit()

        # Get next person (should wrap to user1)
        next_person = await service.get_next_person(team, date.today())

        assert next_person is not None
        assert next_person.id == user1.id

    @pytest.mark.asyncio
    async def test_get_next_person_last_assigned_not_in_list(self, setup_rotation_service, db_session: AsyncSession):
        """Test next person when last assigned user is not in current member list"""
        service, workspace, team, user1, user2, user3 = setup_rotation_service

        # Create another user not in the rotation
        user4 = User(
            workspace_id=workspace.id,
            telegram_username="user4",
            first_name="User",
            last_name="Four",
            display_name="User Four"
        )
        db_session.add(user4)
        await db_session.commit()
        await db_session.refresh(user4)

        # Create rotation config with user4 as last assigned but not in member_ids
        config = RotationConfig(
            team_id=team.id,
            enabled=True,
            member_ids=[user1.id, user2.id, user3.id],
            last_assigned_user_id=user4.id
        )
        db_session.add(config)
        await db_session.commit()

        # Get next person (should start from beginning)
        next_person = await service.get_next_person(team, date.today())

        assert next_person is not None
        assert next_person.id == user1.id

    @pytest.mark.asyncio
    async def test_get_next_person_no_config(self, setup_rotation_service):
        """Test getting next person when no rotation config exists"""
        service, workspace, team, user1, user2, user3 = setup_rotation_service

        next_person = await service.get_next_person(team, date.today())

        assert next_person is None

    @pytest.mark.asyncio
    async def test_get_next_person_rotation_disabled(self, setup_rotation_service, db_session: AsyncSession):
        """Test getting next person when rotation is disabled"""
        service, workspace, team, user1, user2, user3 = setup_rotation_service

        # Create disabled rotation config
        config = RotationConfig(
            team_id=team.id,
            enabled=False,
            member_ids=[user1.id, user2.id, user3.id]
        )
        db_session.add(config)
        await db_session.commit()

        next_person = await service.get_next_person(team, date.today())

        assert next_person is None

    @pytest.mark.asyncio
    async def test_get_next_person_empty_member_ids(self, setup_rotation_service, db_session: AsyncSession):
        """Test getting next person when member_ids is empty"""
        service, workspace, team, user1, user2, user3 = setup_rotation_service

        # Create rotation config with empty member list
        config = RotationConfig(
            team_id=team.id,
            enabled=True,
            member_ids=[]
        )
        db_session.add(config)
        await db_session.commit()

        next_person = await service.get_next_person(team, date.today())

        assert next_person is None

    @pytest.mark.asyncio
    async def test_get_next_person_without_user_repo(self, setup_rotation_service, db_session: AsyncSession):
        """Test getting next person when user_repo is None"""
        service, workspace, team, user1, user2, user3 = setup_rotation_service

        # Create service without user_repo
        rotation_config_repo = RotationConfigRepository(db_session)
        service_without_user_repo = RotationService(rotation_config_repo, None, None)

        # Create rotation config
        config = RotationConfig(
            team_id=team.id,
            enabled=True,
            member_ids=[user1.id, user2.id],
            last_assigned_user_id=None
        )
        db_session.add(config)
        await db_session.commit()

        # Get next person
        next_person = await service_without_user_repo.get_next_person(team, date.today())

        # Should return stub user with just ID
        assert next_person is not None
        assert next_person.id == user1.id

    @pytest.mark.asyncio
    async def test_assign_rotation(self, setup_rotation_service, db_session: AsyncSession):
        """Test assigning next person in rotation"""
        service, workspace, team, user1, user2, user3 = setup_rotation_service

        # Create rotation config
        config = RotationConfig(
            team_id=team.id,
            enabled=True,
            member_ids=[user1.id, user2.id, user3.id],
            last_assigned_user_id=None
        )
        db_session.add(config)
        await db_session.commit()

        assignment_date = date.today() + timedelta(days=1)
        assigned_user, message = await service.assign_rotation(team, assignment_date)

        assert assigned_user is not None
        assert assigned_user.id == user1.id
        assert "User One" in message
        assert assignment_date.strftime('%d.%m.%Y') in message

        # Verify rotation config was updated
        updated_config = await service.get_rotation_config(team)
        assert updated_config.last_assigned_user_id == user1.id
        assert updated_config.last_assigned_date == assignment_date

    @pytest.mark.asyncio
    async def test_assign_rotation_creates_schedule(self, setup_rotation_service, db_session: AsyncSession):
        """Test that assign_rotation creates a schedule entry"""
        service, workspace, team, user1, user2, user3 = setup_rotation_service

        # Create rotation config
        config = RotationConfig(
            team_id=team.id,
            enabled=True,
            member_ids=[user1.id, user2.id],
            last_assigned_user_id=None
        )
        db_session.add(config)
        await db_session.commit()

        assignment_date = date.today() + timedelta(days=1)
        assigned_user, message = await service.assign_rotation(team, assignment_date)

        # Verify schedule was created
        schedule_repo = ScheduleRepository(db_session)
        schedule = await schedule_repo.get_by_team_and_date(team.id, assignment_date)
        assert schedule is not None
        assert schedule.user_id == user1.id

    @pytest.mark.asyncio
    async def test_assign_rotation_disabled(self, setup_rotation_service, db_session: AsyncSession):
        """Test assigning rotation when rotation is disabled"""
        service, workspace, team, user1, user2, user3 = setup_rotation_service

        # Create disabled rotation config
        config = RotationConfig(
            team_id=team.id,
            enabled=False,
            member_ids=[user1.id, user2.id]
        )
        db_session.add(config)
        await db_session.commit()

        assignment_date = date.today()
        assigned_user, message = await service.assign_rotation(team, assignment_date)

        assert assigned_user is None
        assert "not enabled" in message

    @pytest.mark.asyncio
    async def test_assign_rotation_no_config(self, setup_rotation_service):
        """Test assigning rotation when no config exists"""
        service, workspace, team, user1, user2, user3 = setup_rotation_service

        assignment_date = date.today()
        assigned_user, message = await service.assign_rotation(team, assignment_date)

        assert assigned_user is None
        assert "not enabled" in message

    @pytest.mark.asyncio
    async def test_assign_rotation_no_members(self, setup_rotation_service, db_session: AsyncSession):
        """Test assigning rotation when no members configured"""
        service, workspace, team, user1, user2, user3 = setup_rotation_service

        # Create rotation config with empty member list
        config = RotationConfig(
            team_id=team.id,
            enabled=True,
            member_ids=[]
        )
        db_session.add(config)
        await db_session.commit()

        assignment_date = date.today()
        assigned_user, message = await service.assign_rotation(team, assignment_date)

        assert assigned_user is None
        assert "No members configured" in message

    @pytest.mark.asyncio
    async def test_assign_rotation_without_schedule_repo(self, setup_rotation_service, db_session: AsyncSession):
        """Test assigning rotation when schedule_repo is None"""
        service, workspace, team, user1, user2, user3 = setup_rotation_service

        # Create service without schedule_repo
        rotation_config_repo = RotationConfigRepository(db_session)
        user_repo = UserRepository(db_session)
        service_without_schedule = RotationService(rotation_config_repo, None, user_repo)

        # Create rotation config
        config = RotationConfig(
            team_id=team.id,
            enabled=True,
            member_ids=[user1.id, user2.id],
            last_assigned_user_id=None
        )
        db_session.add(config)
        await db_session.commit()

        assignment_date = date.today()
        assigned_user, message = await service_without_schedule.assign_rotation(team, assignment_date)

        # Should still assign but not create schedule
        assert assigned_user is not None
        assert assigned_user.id == user1.id

    @pytest.mark.asyncio
    async def test_update_member_order(self, setup_rotation_service, db_session: AsyncSession):
        """Test updating member order in rotation"""
        service, workspace, team, user1, user2, user3 = setup_rotation_service

        # Create rotation config
        config = RotationConfig(
            team_id=team.id,
            enabled=True,
            member_ids=[user1.id, user2.id, user3.id]
        )
        db_session.add(config)
        await db_session.commit()

        # Update member order (reverse)
        new_member_ids = [user3.id, user2.id, user1.id]
        updated_config = await service.update_member_order(team, new_member_ids)

        assert updated_config is not None
        assert updated_config.member_ids == new_member_ids

    @pytest.mark.asyncio
    async def test_update_member_order_no_config(self, setup_rotation_service):
        """Test updating member order when no config exists"""
        service, workspace, team, user1, user2, user3 = setup_rotation_service

        new_member_ids = [user1.id, user2.id]

        with pytest.raises(ValueError, match="No rotation config"):
            await service.update_member_order(team, new_member_ids)

    @pytest.mark.asyncio
    async def test_get_rotation_status_no_config(self, setup_rotation_service):
        """Test getting rotation status when no config exists"""
        service, workspace, team, user1, user2, user3 = setup_rotation_service

        status = await service.get_rotation_status(team)

        assert status == "No rotation configured"

    @pytest.mark.asyncio
    async def test_get_rotation_status_disabled(self, setup_rotation_service, db_session: AsyncSession):
        """Test getting rotation status when disabled"""
        service, workspace, team, user1, user2, user3 = setup_rotation_service

        # Create disabled rotation config
        config = RotationConfig(
            team_id=team.id,
            enabled=False,
            member_ids=[user1.id, user2.id]
        )
        db_session.add(config)
        await db_session.commit()

        status = await service.get_rotation_status(team)

        assert status == "Rotation is disabled"

    @pytest.mark.asyncio
    async def test_get_rotation_status_enabled_with_members(self, setup_rotation_service, db_session: AsyncSession):
        """Test getting rotation status when enabled with members"""
        service, workspace, team, user1, user2, user3 = setup_rotation_service

        # Create rotation config
        config = RotationConfig(
            team_id=team.id,
            enabled=True,
            member_ids=[user1.id, user2.id, user3.id],
            last_assigned_user_id=user1.id,
            last_assigned_date=date(2024, 1, 15)
        )
        db_session.add(config)
        await db_session.commit()

        status = await service.get_rotation_status(team)

        assert "Rotation enabled" in status
        assert "User One" in status
        assert "User Two" in status
        assert "User Three" in status
        assert "→" in status  # Arrow separator
        assert "Last assigned: User One" in status
        assert "15.01.2024" in status

    @pytest.mark.asyncio
    async def test_get_rotation_status_no_last_assigned(self, setup_rotation_service, db_session: AsyncSession):
        """Test getting rotation status when no one has been assigned yet"""
        service, workspace, team, user1, user2, user3 = setup_rotation_service

        # Create rotation config without last assigned
        config = RotationConfig(
            team_id=team.id,
            enabled=True,
            member_ids=[user1.id, user2.id],
            last_assigned_user_id=None,
            last_assigned_date=None
        )
        db_session.add(config)
        await db_session.commit()

        status = await service.get_rotation_status(team)

        assert "Rotation enabled" in status
        assert "User One" in status
        assert "User Two" in status
        assert "Last assigned" not in status

    @pytest.mark.asyncio
    async def test_get_rotation_status_without_user_repo(self, setup_rotation_service, db_session: AsyncSession):
        """Test getting rotation status when user_repo is None"""
        service, workspace, team, user1, user2, user3 = setup_rotation_service

        # Create service without user_repo
        rotation_config_repo = RotationConfigRepository(db_session)
        service_without_user_repo = RotationService(rotation_config_repo, None, None)

        # Create rotation config
        config = RotationConfig(
            team_id=team.id,
            enabled=True,
            member_ids=[user1.id, user2.id],
            last_assigned_user_id=user1.id,
            last_assigned_date=date(2024, 1, 15)
        )
        db_session.add(config)
        await db_session.commit()

        status = await service_without_user_repo.get_rotation_status(team)

        assert "Rotation enabled" in status
        assert "No members" in status
        assert f"Last assigned: User {user1.id}" in status

    @pytest.mark.asyncio
    async def test_get_rotation_status_member_not_found(self, setup_rotation_service, db_session: AsyncSession):
        """Test getting rotation status when a member user is not found"""
        service, workspace, team, user1, user2, user3 = setup_rotation_service

        # Create rotation config with non-existent user ID
        config = RotationConfig(
            team_id=team.id,
            enabled=True,
            member_ids=[user1.id, 99999],  # 99999 doesn't exist
            last_assigned_user_id=None
        )
        db_session.add(config)
        await db_session.commit()

        status = await service.get_rotation_status(team)

        assert "Rotation enabled" in status
        assert "User One" in status
        assert "User 99999" in status  # Fallback for non-existent user

    @pytest.mark.asyncio
    async def test_rotation_sequence_multiple_assignments(self, setup_rotation_service, db_session: AsyncSession):
        """Test complete rotation sequence with multiple assignments"""
        service, workspace, team, user1, user2, user3 = setup_rotation_service

        # Create rotation config
        config = RotationConfig(
            team_id=team.id,
            enabled=True,
            member_ids=[user1.id, user2.id, user3.id],
            last_assigned_user_id=None
        )
        db_session.add(config)
        await db_session.commit()

        # First assignment
        date1 = date.today()
        assigned1, msg1 = await service.assign_rotation(team, date1)
        assert assigned1.id == user1.id

        # Second assignment
        date2 = date.today() + timedelta(days=1)
        assigned2, msg2 = await service.assign_rotation(team, date2)
        assert assigned2.id == user2.id

        # Third assignment
        date3 = date.today() + timedelta(days=2)
        assigned3, msg3 = await service.assign_rotation(team, date3)
        assert assigned3.id == user3.id

        # Fourth assignment (should wrap to user1)
        date4 = date.today() + timedelta(days=3)
        assigned4, msg4 = await service.assign_rotation(team, date4)
        assert assigned4.id == user1.id
