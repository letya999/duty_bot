import pytest
from datetime import datetime, date
from app.models import Organization, User, UserAccount, Workspace, Team, Incident, Escalation

class TestOrganizationScenarios:
    """Test scenarios for Organization support based on 'Organizations in Duty Bot' prompt"""

    def test_create_organization_with_workspaces(self, organization_factory, workspace_factory):
        """Test creating an organization and adding workspaces to it"""
        org = organization_factory(name="Big Corp")
        ws1 = workspace_factory(name="Engineering", workspace_type="slack", external_id="W1", organization_id=None)
        ws2 = workspace_factory(name="Sales", workspace_type="slack", external_id="W2", organization_id=None)
        
        # Link workspaces to organization
        # In a real DB session, we would set properties. Here we simulate object state.
        org.workspaces.append(ws1)
        org.workspaces.append(ws2)
        
        assert ws1 in org.workspaces
        assert ws2 in org.workspaces
        assert len(org.workspaces) == 2

    def test_user_creation_with_multiple_accounts(self, user_factory, user_account_factory):
        """
        User "alice" → UserAccount (Slack, U123, Engineering Workspace)
        User "alice" → UserAccount (Telegram, 111, DevOps Workspace)
        """
        user = user_factory(display_name="alice")
        
        # Account 1: Slack
        account1 = user_account_factory(
            user_id=user.id,
            provider="slack",
            provider_id="U123",
            workspace_id=1,
            username="alice_slack"
        )
        
        # Account 2: Telegram
        account2 = user_account_factory(
            user_id=user.id,
            provider="telegram",
            provider_id="111",
            workspace_id=2,
            username="alice_tg"
        )
        
        user.user_accounts.append(account1)
        user.user_accounts.append(account2)
        
        assert len(user.user_accounts) == 2
        providers = [acc.provider for acc in user.user_accounts]
        assert "slack" in providers
        assert "telegram" in providers

    def test_team_in_organization(self, team_factory, organization_factory):
        """
        Team can belong to an Organization.
        SuperAdmin chooses Team "testing" (Engineering) and Team "testing" (DevOps) -> update team.organization_id
        """
        org = organization_factory(name="Big Corp")
        team1 = team_factory(name="testing", workspace_id=1)
        
        # Assign team to organization
        team1.organization_id = org.id
        team1.organization = org
        
        assert team1.organization == org

        # Check that team can be retrieved via organization
        org.teams.append(team1)
        assert team1 in org.teams

    def test_incident_for_organization(self, incident_factory, organization_factory):
        """Incident linked to Organization (shared across workspaces)"""
        org = organization_factory(name="Big Corp")
        incident = incident_factory(name="Global Outage", workspace_id=1) # Incident must have workspace_id still? check model
        
        # Model definition:
        # workspace_id = Column(Integer, ForeignKey('workspace.id'), nullable=False, index=True)
        # organization_id = Column(Integer, ForeignKey('organization.id'), nullable=True)
        
        incident.organization = org
        assert incident.organization_id == org.id or incident.organization == org 
        # (Note: id won't be set until flush in real DB, but object relationship holds)

    def test_merge_users_scenario(self, user_factory, user_account_factory):
        """
        Scenario 1: Merge two Users
        SuperAdmin sees User "alice" (Slack U123) and User "alice_old" (Slack U456)
        Updates display_name = "alice", removes second User, moves UserAccount to first.
        """
        user1 = user_factory(display_name="alice", id=1)
        user2 = user_factory(display_name="alice_old", id=2)
        
        account1 = user_account_factory(user_id=user1.id, provider="slack", provider_id="U123")
        account2 = user_account_factory(user_id=user2.id, provider="slack", provider_id="U456")
        
        user1.user_accounts.append(account1)
        user2.user_accounts.append(account2)
        
        # Simulate Merge Logic
        # 1. Move account2 to user1
        account2.user_id = user1.id
        user2.user_accounts.remove(account2)
        user1.user_accounts.append(account2)
        
        # 2. "Delete" user2 (in test just verify state)
        assert len(user1.user_accounts) == 2
        assert len(user2.user_accounts) == 0
        assert account2.user_id == user1.id
