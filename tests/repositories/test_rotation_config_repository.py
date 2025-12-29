import pytest
from datetime import date
from sqlalchemy.ext.asyncio import AsyncSession
from app.repositories.rotation_config_repository import RotationConfigRepository
from app.models import Workspace, Team, User, RotationConfig


class TestRotationConfigRepository:
    """Test RotationConfigRepository methods"""

    @pytest.fixture
    async def setup_rotation_config_repo(self, db_session: AsyncSession):
        """Setup rotation config repository with test data"""
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
            username="user1",
            first_name="User",
            last_name="One"
        )
        user2 = User(
            workspace_id=workspace.id,
            username="user2",
            first_name="User",
            last_name="Two"
        )
        db_session.add(user1)
        db_session.add(user2)
        await db_session.commit()
        await db_session.refresh(user1)
        await db_session.refresh(user2)

        repo = RotationConfigRepository(db_session)
        return repo, workspace, team, user1, user2

    @pytest.mark.asyncio
    async def test_get_by_team_exists(self, setup_rotation_config_repo):
        """Test getting rotation config by team when it exists"""
        repo, workspace, team, user1, user2 = setup_rotation_config_repo

        # Create rotation config
        config = RotationConfig(
            team_id=team.id,
            enabled=True,
            member_ids=[user1.id, user2.id]
        )
        repo.db.add(config)
        await repo.db.commit()
        await repo.db.refresh(config)

        # Get by team
        found_config = await repo.get_by_team(team.id)

        assert found_config is not None
        assert found_config.team_id == team.id
        assert found_config.enabled is True
        assert found_config.member_ids == [user1.id, user2.id]

    @pytest.mark.asyncio
    async def test_get_by_team_not_found(self, setup_rotation_config_repo):
        """Test getting rotation config when none exists"""
        repo, workspace, team, user1, user2 = setup_rotation_config_repo

        config = await repo.get_by_team(team.id)

        assert config is None

    @pytest.mark.asyncio
    async def test_get_by_team_wrong_team(self, setup_rotation_config_repo, db_session: AsyncSession):
        """Test getting rotation config for wrong team"""
        repo, workspace, team, user1, user2 = setup_rotation_config_repo

        # Create config for team
        config = RotationConfig(
            team_id=team.id,
            enabled=True,
            member_ids=[user1.id]
        )
        repo.db.add(config)
        await repo.db.commit()

        # Try to get for non-existent team
        found_config = await repo.get_by_team(9999)

        assert found_config is None

    @pytest.mark.asyncio
    async def test_update_member_list(self, setup_rotation_config_repo):
        """Test updating member list"""
        repo, workspace, team, user1, user2 = setup_rotation_config_repo

        # Create rotation config
        config = RotationConfig(
            team_id=team.id,
            enabled=True,
            member_ids=[user1.id]
        )
        repo.db.add(config)
        await repo.db.commit()

        # Update member list
        new_member_ids = [user1.id, user2.id]
        updated_config = await repo.update_member_list(team.id, new_member_ids)

        assert updated_config is not None
        assert updated_config.member_ids == new_member_ids

    @pytest.mark.asyncio
    async def test_update_member_list_no_config(self, setup_rotation_config_repo):
        """Test updating member list when no config exists"""
        repo, workspace, team, user1, user2 = setup_rotation_config_repo

        updated_config = await repo.update_member_list(team.id, [user1.id, user2.id])

        assert updated_config is None

    @pytest.mark.asyncio
    async def test_update_member_list_empty(self, setup_rotation_config_repo):
        """Test updating member list to empty list"""
        repo, workspace, team, user1, user2 = setup_rotation_config_repo

        # Create rotation config
        config = RotationConfig(
            team_id=team.id,
            enabled=True,
            member_ids=[user1.id, user2.id]
        )
        repo.db.add(config)
        await repo.db.commit()

        # Update to empty list
        updated_config = await repo.update_member_list(team.id, [])

        assert updated_config is not None
        assert updated_config.member_ids == []

    @pytest.mark.asyncio
    async def test_update_last_assigned(self, setup_rotation_config_repo):
        """Test updating last assigned user and date"""
        repo, workspace, team, user1, user2 = setup_rotation_config_repo

        # Create rotation config
        config = RotationConfig(
            team_id=team.id,
            enabled=True,
            member_ids=[user1.id, user2.id],
            last_assigned_user_id=None,
            last_assigned_date=None
        )
        repo.db.add(config)
        await repo.db.commit()

        # Update last assigned
        assigned_date = date(2024, 1, 15)
        updated_config = await repo.update_last_assigned(team.id, user1.id, assigned_date)

        assert updated_config is not None
        assert updated_config.last_assigned_user_id == user1.id
        assert updated_config.last_assigned_date == assigned_date

    @pytest.mark.asyncio
    async def test_update_last_assigned_no_config(self, setup_rotation_config_repo):
        """Test updating last assigned when no config exists"""
        repo, workspace, team, user1, user2 = setup_rotation_config_repo

        updated_config = await repo.update_last_assigned(team.id, user1.id, date.today())

        assert updated_config is None

    @pytest.mark.asyncio
    async def test_update_last_assigned_change_user(self, setup_rotation_config_repo):
        """Test updating last assigned to different user"""
        repo, workspace, team, user1, user2 = setup_rotation_config_repo

        # Create rotation config with user1 assigned
        config = RotationConfig(
            team_id=team.id,
            enabled=True,
            member_ids=[user1.id, user2.id],
            last_assigned_user_id=user1.id,
            last_assigned_date=date(2024, 1, 10)
        )
        repo.db.add(config)
        await repo.db.commit()

        # Update to user2
        new_date = date(2024, 1, 15)
        updated_config = await repo.update_last_assigned(team.id, user2.id, new_date)

        assert updated_config is not None
        assert updated_config.last_assigned_user_id == user2.id
        assert updated_config.last_assigned_date == new_date

    @pytest.mark.asyncio
    async def test_toggle_enabled_enable(self, setup_rotation_config_repo):
        """Test enabling rotation via toggle_enabled"""
        repo, workspace, team, user1, user2 = setup_rotation_config_repo

        # Create disabled rotation config
        config = RotationConfig(
            team_id=team.id,
            enabled=False,
            member_ids=[user1.id, user2.id]
        )
        repo.db.add(config)
        await repo.db.commit()

        # Enable it
        updated_config = await repo.toggle_enabled(team.id, True)

        assert updated_config is not None
        assert updated_config.enabled is True

    @pytest.mark.asyncio
    async def test_toggle_enabled_disable(self, setup_rotation_config_repo):
        """Test disabling rotation via toggle_enabled"""
        repo, workspace, team, user1, user2 = setup_rotation_config_repo

        # Create enabled rotation config
        config = RotationConfig(
            team_id=team.id,
            enabled=True,
            member_ids=[user1.id, user2.id]
        )
        repo.db.add(config)
        await repo.db.commit()

        # Disable it
        updated_config = await repo.toggle_enabled(team.id, False)

        assert updated_config is not None
        assert updated_config.enabled is False

    @pytest.mark.asyncio
    async def test_toggle_enabled_no_config(self, setup_rotation_config_repo):
        """Test toggle_enabled when no config exists"""
        repo, workspace, team, user1, user2 = setup_rotation_config_repo

        updated_config = await repo.toggle_enabled(team.id, True)

        assert updated_config is None

    @pytest.mark.asyncio
    async def test_enable_rotation_creates_new_config(self, setup_rotation_config_repo):
        """Test enable_rotation creates new config when none exists"""
        repo, workspace, team, user1, user2 = setup_rotation_config_repo

        member_ids = [user1.id, user2.id]
        config = await repo.enable_rotation(team.id, member_ids)

        assert config is not None
        assert config.team_id == team.id
        assert config.enabled is True
        assert config.member_ids == member_ids
        assert config.last_assigned_user_id == user1.id

    @pytest.mark.asyncio
    async def test_enable_rotation_creates_with_empty_members(self, setup_rotation_config_repo):
        """Test enable_rotation with empty member list"""
        repo, workspace, team, user1, user2 = setup_rotation_config_repo

        config = await repo.enable_rotation(team.id, [])

        assert config is not None
        assert config.enabled is True
        assert config.member_ids == []
        assert config.last_assigned_user_id is None

    @pytest.mark.asyncio
    async def test_enable_rotation_updates_existing_config(self, setup_rotation_config_repo):
        """Test enable_rotation updates existing config"""
        repo, workspace, team, user1, user2 = setup_rotation_config_repo

        # Create existing config
        existing_config = RotationConfig(
            team_id=team.id,
            enabled=False,
            member_ids=[user1.id],
            last_assigned_user_id=None
        )
        repo.db.add(existing_config)
        await repo.db.commit()
        await repo.db.refresh(existing_config)
        config_id = existing_config.id

        # Enable rotation with new members
        member_ids = [user1.id, user2.id]
        config = await repo.enable_rotation(team.id, member_ids)

        assert config.id == config_id  # Same config updated
        assert config.enabled is True
        assert config.member_ids == member_ids

    @pytest.mark.asyncio
    async def test_enable_rotation_preserves_last_assigned_if_set(self, setup_rotation_config_repo):
        """Test enable_rotation preserves last_assigned_user_id if already set"""
        repo, workspace, team, user1, user2 = setup_rotation_config_repo

        # Create existing config with last_assigned_user_id set
        existing_config = RotationConfig(
            team_id=team.id,
            enabled=False,
            member_ids=[user1.id],
            last_assigned_user_id=user1.id
        )
        repo.db.add(existing_config)
        await repo.db.commit()

        # Enable rotation
        member_ids = [user1.id, user2.id]
        config = await repo.enable_rotation(team.id, member_ids)

        # Should preserve existing last_assigned_user_id
        assert config.last_assigned_user_id == user1.id

    @pytest.mark.asyncio
    async def test_enable_rotation_sets_last_assigned_if_not_set(self, setup_rotation_config_repo):
        """Test enable_rotation sets last_assigned_user_id if not set"""
        repo, workspace, team, user1, user2 = setup_rotation_config_repo

        # Create existing config without last_assigned_user_id
        existing_config = RotationConfig(
            team_id=team.id,
            enabled=False,
            member_ids=[user2.id],
            last_assigned_user_id=None
        )
        repo.db.add(existing_config)
        await repo.db.commit()

        # Enable rotation with new members
        member_ids = [user1.id, user2.id]
        config = await repo.enable_rotation(team.id, member_ids)

        # Should set to first member
        assert config.last_assigned_user_id == user1.id

    @pytest.mark.asyncio
    async def test_update_last_assigned_for_rotation(self, setup_rotation_config_repo):
        """Test update_last_assigned_for_rotation"""
        repo, workspace, team, user1, user2 = setup_rotation_config_repo

        # Create rotation config
        config = RotationConfig(
            team_id=team.id,
            enabled=True,
            member_ids=[user1.id, user2.id],
            last_assigned_user_id=None,
            last_assigned_date=None
        )
        repo.db.add(config)
        await repo.db.commit()

        # Update last assigned for rotation
        assigned_date = date(2024, 1, 15)
        updated_config = await repo.update_last_assigned_for_rotation(
            team.id, user1.id, assigned_date
        )

        assert updated_config is not None
        assert updated_config.last_assigned_user_id == user1.id
        assert updated_config.last_assigned_date == assigned_date

    @pytest.mark.asyncio
    async def test_update_last_assigned_for_rotation_no_config(self, setup_rotation_config_repo):
        """Test update_last_assigned_for_rotation when no config exists"""
        repo, workspace, team, user1, user2 = setup_rotation_config_repo

        updated_config = await repo.update_last_assigned_for_rotation(
            team.id, user1.id, date.today()
        )

        assert updated_config is None

    @pytest.mark.asyncio
    async def test_update_last_assigned_for_rotation_updates_both_fields(
        self, setup_rotation_config_repo
    ):
        """Test update_last_assigned_for_rotation updates both user and date"""
        repo, workspace, team, user1, user2 = setup_rotation_config_repo

        # Create rotation config
        config = RotationConfig(
            team_id=team.id,
            enabled=True,
            member_ids=[user1.id, user2.id],
            last_assigned_user_id=user1.id,
            last_assigned_date=date(2024, 1, 10)
        )
        repo.db.add(config)
        await repo.db.commit()

        # Update to new user and date
        new_date = date(2024, 1, 15)
        updated_config = await repo.update_last_assigned_for_rotation(
            team.id, user2.id, new_date
        )

        assert updated_config.last_assigned_user_id == user2.id
        assert updated_config.last_assigned_date == new_date

    @pytest.mark.asyncio
    async def test_create_rotation_config_via_base_repository(self, setup_rotation_config_repo):
        """Test creating rotation config using base repository create method"""
        repo, workspace, team, user1, user2 = setup_rotation_config_repo

        # Use base repository create method
        config = await repo.create({
            'team_id': team.id,
            'enabled': True,
            'member_ids': [user1.id, user2.id],
            'last_assigned_user_id': user1.id,
            'last_assigned_date': date(2024, 1, 15)
        })

        assert config is not None
        assert config.id is not None
        assert config.team_id == team.id
        assert config.enabled is True

    @pytest.mark.asyncio
    async def test_delete_rotation_config(self, setup_rotation_config_repo):
        """Test deleting rotation config"""
        repo, workspace, team, user1, user2 = setup_rotation_config_repo

        # Create rotation config
        config = RotationConfig(
            team_id=team.id,
            enabled=True,
            member_ids=[user1.id, user2.id]
        )
        repo.db.add(config)
        await repo.db.commit()
        await repo.db.refresh(config)
        config_id = config.id

        # Delete using base repository method
        success = await repo.delete(config_id)

        assert success is True

        # Verify it's deleted
        found_config = await repo.get_by_team(team.id)
        assert found_config is None

    @pytest.mark.asyncio
    async def test_get_by_id_rotation_config(self, setup_rotation_config_repo):
        """Test getting rotation config by ID using base repository"""
        repo, workspace, team, user1, user2 = setup_rotation_config_repo

        # Create rotation config
        config = RotationConfig(
            team_id=team.id,
            enabled=True,
            member_ids=[user1.id, user2.id]
        )
        repo.db.add(config)
        await repo.db.commit()
        await repo.db.refresh(config)

        # Get by ID
        found_config = await repo.get_by_id(config.id)

        assert found_config is not None
        assert found_config.id == config.id
        assert found_config.team_id == team.id

    @pytest.mark.asyncio
    async def test_rotation_config_unique_per_team(self, setup_rotation_config_repo, db_session: AsyncSession):
        """Test that rotation config is unique per team"""
        repo, workspace, team, user1, user2 = setup_rotation_config_repo

        # Create first config
        config1 = RotationConfig(
            team_id=team.id,
            enabled=True,
            member_ids=[user1.id]
        )
        repo.db.add(config1)
        await repo.db.commit()

        # Try to create second config for same team - should raise error
        config2 = RotationConfig(
            team_id=team.id,
            enabled=False,
            member_ids=[user2.id]
        )
        repo.db.add(config2)

        with pytest.raises(Exception):  # Will raise integrity error
            await repo.db.commit()

    @pytest.mark.asyncio
    async def test_rotation_config_multiple_teams(self, setup_rotation_config_repo, db_session: AsyncSession):
        """Test multiple rotation configs for different teams"""
        repo, workspace, team, user1, user2 = setup_rotation_config_repo

        # Create another team
        team2 = Team(
            workspace_id=workspace.id,
            name="frontend",
            display_name="Frontend Team"
        )
        db_session.add(team2)
        await db_session.commit()
        await db_session.refresh(team2)

        # Create config for first team
        config1 = await repo.enable_rotation(team.id, [user1.id])

        # Create config for second team
        config2 = await repo.enable_rotation(team2.id, [user2.id])

        assert config1.team_id == team.id
        assert config2.team_id == team2.id
        assert config1.id != config2.id

        # Verify both can be retrieved
        found_config1 = await repo.get_by_team(team.id)
        found_config2 = await repo.get_by_team(team2.id)

        assert found_config1 is not None
        assert found_config2 is not None
        assert found_config1.id == config1.id
        assert found_config2.id == config2.id
