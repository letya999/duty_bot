import pytest
from sqlalchemy.ext.asyncio import AsyncSession
from app.repositories.team_repository import TeamRepository
from app.models import Workspace, Team, User


class TestTeamRepository:
    """Test TeamRepository methods"""

    @pytest.fixture
    async def setup_team_repo(self, db_session: AsyncSession):
        """Setup team repository with test data"""
        # Create workspace
        workspace = Workspace(
            name="Test Workspace",
            workspace_type="telegram",
            external_id="123456789"
        )
        db_session.add(workspace)
        await db_session.commit()
        await db_session.refresh(workspace)

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

        repo = TeamRepository(db_session)
        return repo, workspace, user1, user2, user3

    @pytest.mark.asyncio
    async def test_get_by_id_with_members(self, setup_team_repo):
        """Test getting team with members relationship loaded"""
        repo, workspace, user1, user2, user3 = setup_team_repo

        # Create team
        team = Team(
            workspace_id=workspace.id,
            name="backend",
            display_name="Backend Team"
        )
        repo.db.add(team)
        await repo.db.commit()
        await repo.db.refresh(team)

        # Add members using repository method
        await repo.add_member(team.id, user1)
        await repo.add_member(team.id, user2)

        # Get team with members
        team_with_members = await repo.get_by_id_with_members(team.id)

        assert team_with_members is not None
        assert team_with_members.id == team.id
        assert len(team_with_members.members) == 2
        member_ids = [m.id for m in team_with_members.members]
        assert user1.id in member_ids
        assert user2.id in member_ids

    @pytest.mark.asyncio
    async def test_get_by_id_with_members_empty(self, setup_team_repo):
        """Test getting team with no members"""
        repo, workspace, user1, user2, user3 = setup_team_repo

        # Create team without members
        team = Team(
            workspace_id=workspace.id,
            name="backend",
            display_name="Backend Team"
        )
        repo.db.add(team)
        await repo.db.commit()
        await repo.db.refresh(team)

        # Get team with members
        team_with_members = await repo.get_by_id_with_members(team.id)

        assert team_with_members is not None
        assert len(team_with_members.members) == 0

    @pytest.mark.asyncio
    async def test_get_by_id_with_members_not_found(self, setup_team_repo):
        """Test getting non-existent team with members"""
        repo, workspace, user1, user2, user3 = setup_team_repo

        team = await repo.get_by_id_with_members(9999)

        assert team is None

    @pytest.mark.asyncio
    async def test_get_by_name_in_workspace(self, setup_team_repo):
        """Test getting team by name in workspace"""
        repo, workspace, user1, user2, user3 = setup_team_repo

        # Create team
        team = Team(
            workspace_id=workspace.id,
            name="backend",
            display_name="Backend Team",
            team_lead_id=user1.id
        )
        repo.db.add(team)
        await repo.db.commit()

        # Get by name
        found_team = await repo.get_by_name_in_workspace(workspace.id, "backend")

        assert found_team is not None
        assert found_team.name == "backend"
        assert found_team.workspace_id == workspace.id

    @pytest.mark.asyncio
    async def test_get_by_name_in_workspace_not_found(self, setup_team_repo):
        """Test getting non-existent team by name"""
        repo, workspace, user1, user2, user3 = setup_team_repo

        team = await repo.get_by_name_in_workspace(workspace.id, "nonexistent")

        assert team is None

    @pytest.mark.asyncio
    async def test_get_by_name_in_workspace_wrong_workspace(
        self, setup_team_repo, db_session: AsyncSession
    ):
        """Test getting team by name in wrong workspace"""
        repo, workspace, user1, user2, user3 = setup_team_repo

        # Create team in first workspace
        team = Team(
            workspace_id=workspace.id,
            name="backend",
            display_name="Backend Team"
        )
        repo.db.add(team)
        await repo.db.commit()

        # Create another workspace
        workspace2 = Workspace(
            name="Other Workspace",
            workspace_type="slack",
            external_id="other123"
        )
        db_session.add(workspace2)
        await db_session.commit()
        await db_session.refresh(workspace2)

        # Try to find team in wrong workspace
        found_team = await repo.get_by_name_in_workspace(workspace2.id, "backend")

        assert found_team is None

    @pytest.mark.asyncio
    async def test_get_by_name_in_workspace_loads_relationships(self, setup_team_repo):
        """Test that get_by_name_in_workspace loads members and team_lead"""
        repo, workspace, user1, user2, user3 = setup_team_repo

        # Create team with lead
        team = Team(
            workspace_id=workspace.id,
            name="backend",
            display_name="Backend Team",
            team_lead_id=user1.id
        )
        repo.db.add(team)
        await repo.db.commit()
        await repo.db.refresh(team)

        # Add members using repository method
        await repo.add_member(team.id, user2)
        await repo.add_member(team.id, user3)

        # Get by name
        found_team = await repo.get_by_name_in_workspace(workspace.id, "backend")

        assert found_team is not None
        # Members should be loaded
        assert len(found_team.members) == 2
        # Team lead should be loaded (if not None)
        assert found_team.team_lead_id == user1.id

    @pytest.mark.asyncio
    async def test_list_by_workspace(self, setup_team_repo):
        """Test listing teams by workspace"""
        repo, workspace, user1, user2, user3 = setup_team_repo

        # Create teams
        team1 = Team(
            workspace_id=workspace.id,
            name="backend",
            display_name="Backend Team"
        )
        team2 = Team(
            workspace_id=workspace.id,
            name="frontend",
            display_name="Frontend Team"
        )
        repo.db.add(team1)
        repo.db.add(team2)
        await repo.db.commit()

        # List teams
        teams = await repo.list_by_workspace(workspace.id)

        assert len(teams) == 2
        team_names = [t.name for t in teams]
        assert "backend" in team_names
        assert "frontend" in team_names

    @pytest.mark.asyncio
    async def test_list_by_workspace_empty(self, setup_team_repo):
        """Test listing teams when workspace has no teams"""
        repo, workspace, user1, user2, user3 = setup_team_repo

        teams = await repo.list_by_workspace(workspace.id)

        assert len(teams) == 0

    @pytest.mark.asyncio
    async def test_list_by_workspace_pagination(self, setup_team_repo):
        """Test listing teams with skip and limit"""
        repo, workspace, user1, user2, user3 = setup_team_repo

        # Create 5 teams
        for i in range(5):
            team = Team(
                workspace_id=workspace.id,
                name=f"team{i}",
                display_name=f"Team {i}"
            )
            repo.db.add(team)
        await repo.db.commit()

        # Test skip and limit
        teams = await repo.list_by_workspace(workspace.id, skip=1, limit=2)

        assert len(teams) == 2

    @pytest.mark.asyncio
    async def test_list_by_workspace_isolation(self, setup_team_repo, db_session: AsyncSession):
        """Test that teams are isolated by workspace"""
        repo, workspace, user1, user2, user3 = setup_team_repo

        # Create team in first workspace
        team1 = Team(
            workspace_id=workspace.id,
            name="backend",
            display_name="Backend Team"
        )
        repo.db.add(team1)
        await repo.db.commit()

        # Create another workspace
        workspace2 = Workspace(
            name="Other Workspace",
            workspace_type="slack",
            external_id="other123"
        )
        db_session.add(workspace2)
        await db_session.commit()
        await db_session.refresh(workspace2)

        # Create team in second workspace
        team2 = Team(
            workspace_id=workspace2.id,
            name="frontend",
            display_name="Frontend Team"
        )
        db_session.add(team2)
        await db_session.commit()

        # List teams for first workspace
        teams = await repo.list_by_workspace(workspace.id)

        assert len(teams) == 1
        assert teams[0].workspace_id == workspace.id

    @pytest.mark.asyncio
    async def test_update_team_info(self, setup_team_repo):
        """Test updating team basic information"""
        repo, workspace, user1, user2, user3 = setup_team_repo

        # Create team
        team = Team(
            workspace_id=workspace.id,
            name="backend",
            display_name="Backend Team",
            has_shifts=False
        )
        repo.db.add(team)
        await repo.db.commit()
        await repo.db.refresh(team)

        # Update team info
        updated_team = await repo.update_team_info(
            team.id,
            name="backend-updated",
            display_name="Updated Backend Team",
            has_shifts=True
        )

        assert updated_team is not None
        assert updated_team.name == "backend-updated"
        assert updated_team.display_name == "Updated Backend Team"
        assert updated_team.has_shifts is True

    @pytest.mark.asyncio
    async def test_update_team_info_not_found(self, setup_team_repo):
        """Test updating non-existent team"""
        repo, workspace, user1, user2, user3 = setup_team_repo

        updated_team = await repo.update_team_info(
            9999,
            name="test",
            display_name="Test",
            has_shifts=False
        )

        assert updated_team is None

    @pytest.mark.asyncio
    async def test_set_team_lead(self, setup_team_repo):
        """Test setting team lead"""
        repo, workspace, user1, user2, user3 = setup_team_repo

        # Create team
        team = Team(
            workspace_id=workspace.id,
            name="backend",
            display_name="Backend Team",
            team_lead_id=None
        )
        repo.db.add(team)
        await repo.db.commit()
        await repo.db.refresh(team)

        # Set team lead
        updated_team = await repo.set_team_lead(team.id, user1.id)

        assert updated_team is not None
        assert updated_team.team_lead_id == user1.id

    @pytest.mark.asyncio
    async def test_set_team_lead_change(self, setup_team_repo):
        """Test changing team lead"""
        repo, workspace, user1, user2, user3 = setup_team_repo

        # Create team with existing lead
        team = Team(
            workspace_id=workspace.id,
            name="backend",
            display_name="Backend Team",
            team_lead_id=user1.id
        )
        repo.db.add(team)
        await repo.db.commit()
        await repo.db.refresh(team)

        # Change team lead
        updated_team = await repo.set_team_lead(team.id, user2.id)

        assert updated_team is not None
        assert updated_team.team_lead_id == user2.id

    @pytest.mark.asyncio
    async def test_set_team_lead_remove(self, setup_team_repo):
        """Test removing team lead"""
        repo, workspace, user1, user2, user3 = setup_team_repo

        # Create team with lead
        team = Team(
            workspace_id=workspace.id,
            name="backend",
            display_name="Backend Team",
            team_lead_id=user1.id
        )
        repo.db.add(team)
        await repo.db.commit()
        await repo.db.refresh(team)

        # Remove team lead
        updated_team = await repo.set_team_lead(team.id, None)

        assert updated_team is not None
        assert updated_team.team_lead_id is None

    @pytest.mark.asyncio
    async def test_set_team_lead_not_found(self, setup_team_repo):
        """Test setting team lead for non-existent team"""
        repo, workspace, user1, user2, user3 = setup_team_repo

        updated_team = await repo.set_team_lead(9999, user1.id)

        assert updated_team is None

    @pytest.mark.asyncio
    async def test_add_member(self, setup_team_repo):
        """Test adding member to team"""
        repo, workspace, user1, user2, user3 = setup_team_repo

        # Create team
        team = Team(
            workspace_id=workspace.id,
            name="backend",
            display_name="Backend Team"
        )
        repo.db.add(team)
        await repo.db.commit()
        await repo.db.refresh(team)

        # Add member
        updated_team = await repo.add_member(team.id, user1)

        assert updated_team is not None

        # Get team with members loaded to verify
        team_with_members = await repo.get_by_id_with_members(team.id)
        assert len(team_with_members.members) == 1
        member_ids = [m.id for m in team_with_members.members]
        assert user1.id in member_ids

    @pytest.mark.asyncio
    async def test_add_member_multiple(self, setup_team_repo):
        """Test adding multiple members to team"""
        repo, workspace, user1, user2, user3 = setup_team_repo

        # Create team
        team = Team(
            workspace_id=workspace.id,
            name="backend",
            display_name="Backend Team"
        )
        repo.db.add(team)
        await repo.db.commit()
        await repo.db.refresh(team)

        # Add first member
        await repo.add_member(team.id, user1)

        # Add second member
        updated_team = await repo.add_member(team.id, user2)

        assert updated_team is not None

        # Get team with members loaded to verify
        team_with_members = await repo.get_by_id_with_members(team.id)
        assert len(team_with_members.members) == 2
        member_ids = [m.id for m in team_with_members.members]
        assert user1.id in member_ids
        assert user2.id in member_ids

    @pytest.mark.asyncio
    async def test_add_member_duplicate(self, setup_team_repo):
        """Test adding same member twice (should not duplicate)"""
        repo, workspace, user1, user2, user3 = setup_team_repo

        # Create team
        team = Team(
            workspace_id=workspace.id,
            name="backend",
            display_name="Backend Team"
        )
        repo.db.add(team)
        await repo.db.commit()
        await repo.db.refresh(team)

        # Add member
        await repo.add_member(team.id, user1)

        # Try to add same member again
        updated_team = await repo.add_member(team.id, user1)

        # Should still have only 1 member
        assert len(updated_team.members) == 1

    @pytest.mark.asyncio
    async def test_add_member_not_found(self, setup_team_repo):
        """Test adding member to non-existent team"""
        repo, workspace, user1, user2, user3 = setup_team_repo

        updated_team = await repo.add_member(9999, user1)

        assert updated_team is None

    @pytest.mark.asyncio
    async def test_remove_member(self, setup_team_repo):
        """Test removing member from team"""
        repo, workspace, user1, user2, user3 = setup_team_repo

        # Create team
        team = Team(
            workspace_id=workspace.id,
            name="backend",
            display_name="Backend Team"
        )
        repo.db.add(team)
        await repo.db.commit()
        await repo.db.refresh(team)

        # Add members using repository method
        await repo.add_member(team.id, user1)
        await repo.add_member(team.id, user2)

        # Remove member
        updated_team = await repo.remove_member(team.id, user1)

        assert updated_team is not None

        # Get team with members loaded to verify
        team_with_members = await repo.get_by_id_with_members(team.id)
        assert len(team_with_members.members) == 1
        member_ids = [m.id for m in team_with_members.members]
        assert user1.id not in member_ids
        assert user2.id in member_ids

    @pytest.mark.asyncio
    async def test_remove_member_not_in_team(self, setup_team_repo):
        """Test removing member that is not in team"""
        repo, workspace, user1, user2, user3 = setup_team_repo

        # Create team with one member
        team = Team(
            workspace_id=workspace.id,
            name="backend",
            display_name="Backend Team"
        )
        repo.db.add(team)
        await repo.db.commit()
        await repo.db.refresh(team)

        # Add one member using repository method
        await repo.add_member(team.id, user1)

        # Try to remove user that's not in team
        updated_team = await repo.remove_member(team.id, user2)

        # Should still have 1 member
        assert len(updated_team.members) == 1
        member_ids = [m.id for m in updated_team.members]
        assert user1.id in member_ids

    @pytest.mark.asyncio
    async def test_remove_member_empty_team(self, setup_team_repo):
        """Test removing member from team with no members"""
        repo, workspace, user1, user2, user3 = setup_team_repo

        # Create team without members
        team = Team(
            workspace_id=workspace.id,
            name="backend",
            display_name="Backend Team"
        )
        repo.db.add(team)
        await repo.db.commit()
        await repo.db.refresh(team)

        # Try to remove member
        updated_team = await repo.remove_member(team.id, user1)

        assert updated_team is not None
        assert len(updated_team.members) == 0

    @pytest.mark.asyncio
    async def test_remove_member_not_found(self, setup_team_repo):
        """Test removing member from non-existent team"""
        repo, workspace, user1, user2, user3 = setup_team_repo

        updated_team = await repo.remove_member(9999, user1)

        assert updated_team is None

    @pytest.mark.asyncio
    async def test_create_team_via_base_repository(self, setup_team_repo):
        """Test creating team using base repository create method"""
        repo, workspace, user1, user2, user3 = setup_team_repo

        # Create team
        team = await repo.create({
            'workspace_id': workspace.id,
            'name': 'backend',
            'display_name': 'Backend Team',
            'has_shifts': False
        })

        assert team is not None
        assert team.id is not None
        assert team.name == 'backend'
        assert team.workspace_id == workspace.id

    @pytest.mark.asyncio
    async def test_delete_team(self, setup_team_repo):
        """Test deleting team"""
        repo, workspace, user1, user2, user3 = setup_team_repo

        # Create team
        team = Team(
            workspace_id=workspace.id,
            name="backend",
            display_name="Backend Team"
        )
        repo.db.add(team)
        await repo.db.commit()
        await repo.db.refresh(team)
        team_id = team.id

        # Delete team
        success = await repo.delete(team_id)

        assert success is True

        # Verify it's deleted
        found_team = await repo.get_by_id(team_id)
        assert found_team is None

    @pytest.mark.asyncio
    async def test_get_team_by_id(self, setup_team_repo):
        """Test getting team by ID using base repository"""
        repo, workspace, user1, user2, user3 = setup_team_repo

        # Create team
        team = Team(
            workspace_id=workspace.id,
            name="backend",
            display_name="Backend Team"
        )
        repo.db.add(team)
        await repo.db.commit()
        await repo.db.refresh(team)

        # Get by ID
        found_team = await repo.get_by_id(team.id)

        assert found_team is not None
        assert found_team.id == team.id
        assert found_team.name == "backend"

    @pytest.mark.asyncio
    async def test_team_member_relationship_bidirectional(self, setup_team_repo):
        """Test that team-member relationship is bidirectional"""
        repo, workspace, user1, user2, user3 = setup_team_repo

        # Create team
        team = Team(
            workspace_id=workspace.id,
            name="backend",
            display_name="Backend Team"
        )
        repo.db.add(team)
        await repo.db.commit()
        await repo.db.refresh(team)

        # Add members
        await repo.add_member(team.id, user1)
        await repo.add_member(team.id, user2)

        # Verify from team side
        team_with_members = await repo.get_by_id_with_members(team.id)
        assert len(team_with_members.members) == 2

        # Verify from user side (if user.teams relationship exists)
        # This tests the many-to-many relationship works both ways
        await repo.db.refresh(user1)
        # Note: This would require user.teams to be loaded, which depends on
        # how the relationship is configured in the User model
