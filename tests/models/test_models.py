import pytest
from datetime import datetime, date
from app.models import (
    Workspace, ChatChannel, User, Team, Schedule, RotationConfig,
    Escalation, EscalationEvent, AdminLog, DutyStats, Incident,
    GoogleCalendarIntegration
)


class TestWorkspaceModel:
    """Test Workspace model"""

    def test_workspace_creation(self, workspace_factory):
        """Test creating a workspace"""
        workspace = workspace_factory(
            name="Test Workspace",
            workspace_type="telegram",
            external_id="123456789"
        )
        assert workspace.name == "Test Workspace"
        assert workspace.workspace_type == "telegram"
        assert workspace.external_id == "123456789"
        assert isinstance(workspace.created_at, datetime)

    def test_workspace_defaults(self, workspace_factory):
        """Test workspace defaults"""
        workspace = workspace_factory()
        assert workspace.created_at is not None
        assert workspace.id is None  # Not persisted yet


class TestChatChannelModel:
    """Test ChatChannel model"""

    def test_chat_channel_creation(self, chat_channel_factory):
        """Test creating a chat channel"""
        channel = chat_channel_factory(
            workspace_id=1,
            messenger="telegram",
            external_id="123456789",
            display_name="Test Channel"
        )
        assert channel.workspace_id == 1
        assert channel.messenger == "telegram"
        assert channel.external_id == "123456789"
        assert channel.display_name == "Test Channel"

    def test_chat_channel_slack(self, chat_channel_factory):
        """Test Slack chat channel"""
        channel = chat_channel_factory(
            messenger="slack",
            external_id="C12345678"
        )
        assert channel.messenger == "slack"


class TestUserModel:
    """Test User model"""

    def test_user_creation(self, user_factory):
        """Test creating a user"""
        user = user_factory(
            workspace_id=1,
            telegram_username="testuser",
            first_name="Test",
            last_name="User"
        )
        assert user.workspace_id == 1
        assert user.telegram_username == "testuser"
        assert user.first_name == "Test"
        assert user.last_name == "User"

    def test_user_admin_flag(self, user_factory):
        """Test user admin flag"""
        admin_user = user_factory(is_admin=True)
        regular_user = user_factory(is_admin=False)
        assert admin_user.is_admin is True
        assert regular_user.is_admin is False

    def test_user_slack_id(self, user_factory):
        """Test user with Slack ID"""
        user = user_factory(slack_user_id="U12345678")
        assert user.slack_user_id == "U12345678"

    def test_user_telegram_id(self, user_factory):
        """Test user with Telegram ID"""
        user = user_factory(telegram_id=123456789)
        assert user.telegram_id == 123456789


class TestTeamModel:
    """Test Team model"""

    def test_team_creation(self, team_factory):
        """Test creating a team"""
        team = team_factory(
            workspace_id=1,
            name="backend_team",
            display_name="Backend Team"
        )
        assert team.workspace_id == 1
        assert team.name == "backend_team"
        assert team.display_name == "Backend Team"

    def test_team_with_shifts(self, team_factory):
        """Test team with shifts enabled"""
        team = team_factory(has_shifts=True)
        assert team.has_shifts is True

    def test_team_with_lead(self, team_factory):
        """Test team with a team lead"""
        team = team_factory(team_lead_id=5)
        assert team.team_lead_id == 5


class TestScheduleModel:
    """Test Schedule model"""

    def test_schedule_creation(self, schedule_factory):
        """Test creating a schedule"""
        test_date = date(2024, 1, 15)
        schedule = schedule_factory(
            team_id=1,
            user_id=1,
            date_obj=test_date
        )
        assert schedule.team_id == 1
        assert schedule.user_id == 1
        assert schedule.date == test_date

    def test_schedule_shift(self, schedule_factory):
        """Test shift schedule"""
        schedule = schedule_factory(is_shift=True)
        assert schedule.is_shift is True

    def test_schedule_regular_duty(self, schedule_factory):
        """Test regular duty schedule"""
        schedule = schedule_factory(is_shift=False)
        assert schedule.is_shift is False


class TestRotationConfigModel:
    """Test RotationConfig model"""

    def test_rotation_config_creation(self):
        """Test creating rotation config"""
        config = RotationConfig(
            team_id=1,
            enabled=True,
            member_ids=[1, 2, 3, 4],
            skip_unavailable=False
        )
        assert config.team_id == 1
        assert config.enabled is True
        assert config.member_ids == [1, 2, 3, 4]
        assert config.skip_unavailable is False

    def test_rotation_config_last_assigned(self):
        """Test last assigned user tracking"""
        config = RotationConfig(
            team_id=1,
            enabled=True,
            member_ids=[1, 2, 3],
            last_assigned_user_id=2,
            last_assigned_date=date(2024, 1, 15)
        )
        assert config.last_assigned_user_id == 2
        assert config.last_assigned_date == date(2024, 1, 15)


class TestEscalationModel:
    """Test Escalation model"""

    def test_escalation_creation(self, escalation_factory):
        """Test creating escalation"""
        escalation = escalation_factory(
            team_id=1,
            cto_id=2
        )
        assert escalation.team_id == 1
        assert escalation.cto_id == 2

    def test_escalation_global_cto(self):
        """Test global CTO escalation"""
        escalation = Escalation(team_id=None, cto_id=1)
        assert escalation.team_id is None
        assert escalation.cto_id == 1


class TestEscalationEventModel:
    """Test EscalationEvent model"""

    def test_escalation_event_creation(self):
        """Test creating escalation event"""
        event = EscalationEvent(
            team_id=1,
            messenger="telegram"
        )
        assert event.team_id == 1
        assert event.messenger == "telegram"
        assert event.acknowledged_at is None
        assert event.escalated_to_level2_at is None

    def test_escalation_event_acknowledgement(self):
        """Test escalation event acknowledgement"""
        now = datetime.utcnow()
        event = EscalationEvent(
            team_id=1,
            messenger="slack",
            acknowledged_at=now
        )
        assert event.acknowledged_at == now

    def test_escalation_event_escalation(self):
        """Test escalation to level 2"""
        now = datetime.utcnow()
        event = EscalationEvent(
            team_id=1,
            messenger="telegram",
            escalated_to_level2_at=now
        )
        assert event.escalated_to_level2_at == now


class TestAdminLogModel:
    """Test AdminLog model"""

    def test_admin_log_creation(self):
        """Test creating admin log"""
        log = AdminLog(
            workspace_id=1,
            admin_user_id=1,
            action="added_admin",
            target_user_id=2,
            details='{"role": "admin"}'
        )
        assert log.workspace_id == 1
        assert log.admin_user_id == 1
        assert log.action == "added_admin"
        assert log.target_user_id == 2

    def test_admin_log_different_actions(self):
        """Test different admin actions"""
        actions = ["added_admin", "removed_admin", "changed_schedule", "updated_escalation"]
        for action in actions:
            log = AdminLog(
                workspace_id=1,
                admin_user_id=1,
                action=action
            )
            assert log.action == action


class TestDutyStatsModel:
    """Test DutyStats model"""

    def test_duty_stats_creation(self):
        """Test creating duty stats"""
        stats = DutyStats(
            workspace_id=1,
            team_id=1,
            user_id=1,
            year=2024,
            month=1,
            duty_days=15,
            shift_days=5
        )
        assert stats.workspace_id == 1
        assert stats.team_id == 1
        assert stats.user_id == 1
        assert stats.year == 2024
        assert stats.month == 1
        assert stats.duty_days == 15
        assert stats.shift_days == 5

    def test_duty_stats_all_months(self):
        """Test duty stats for all months"""
        for month in range(1, 13):
            stats = DutyStats(
                workspace_id=1,
                team_id=1,
                user_id=1,
                year=2024,
                month=month
            )
            assert stats.month == month

    def test_duty_stats_hours_worked(self):
        """Test hours worked tracking"""
        stats = DutyStats(
            workspace_id=1,
            team_id=1,
            user_id=1,
            year=2024,
            month=1,
            hours_worked=160
        )
        assert stats.hours_worked == 160


class TestIncidentModel:
    """Test Incident model"""

    def test_incident_creation(self, incident_factory):
        """Test creating incident"""
        start_time = datetime(2024, 1, 15, 10, 30)
        incident = incident_factory(
            workspace_id=1,
            name="Database Connection Error",
            start_time=start_time
        )
        assert incident.workspace_id == 1
        assert incident.name == "Database Connection Error"
        assert incident.start_time == start_time

    def test_incident_status_active(self, incident_factory):
        """Test active incident"""
        incident = incident_factory()
        assert incident.status == "active"
        assert incident.end_time is None

    def test_incident_status_resolved(self, incident_factory):
        """Test resolved incident"""
        start_time = datetime(2024, 1, 15, 10, 30)
        end_time = datetime(2024, 1, 15, 11, 45)
        incident = incident_factory(
            status="resolved",
            start_time=start_time,
            end_time=end_time
        )
        assert incident.status == "resolved"
        assert incident.end_time == end_time

    def test_incident_statuses(self, incident_factory):
        """Test different incident statuses"""
        statuses = ["active", "resolved"]
        for status in statuses:
            incident = incident_factory(status=status)
            assert incident.status == status


class TestGoogleCalendarIntegrationModel:
    """Test GoogleCalendarIntegration model"""

    def test_google_calendar_creation(self):
        """Test creating Google Calendar integration"""
        integration = GoogleCalendarIntegration(
            workspace_id=1,
            service_account_key_encrypted="encrypted_key_here",
            google_calendar_id="calendar@example.com",
            public_calendar_url="https://calendar.google.com/calendar/u/0",
            service_account_email="service@example.iam.gserviceaccount.com",
            is_active=True
        )
        assert integration.workspace_id == 1
        assert integration.google_calendar_id == "calendar@example.com"
        assert integration.is_active is True

    def test_google_calendar_sync_tracking(self):
        """Test sync time tracking"""
        sync_time = datetime(2024, 1, 15, 10, 30)
        integration = GoogleCalendarIntegration(
            workspace_id=1,
            service_account_key_encrypted="key",
            google_calendar_id="cal@example.com",
            public_calendar_url="https://example.com",
            service_account_email="service@example.com",
            last_sync_at=sync_time
        )
        assert integration.last_sync_at == sync_time

    def test_google_calendar_inactive(self):
        """Test inactive calendar integration"""
        integration = GoogleCalendarIntegration(
            workspace_id=1,
            service_account_key_encrypted="key",
            google_calendar_id="cal@example.com",
            public_calendar_url="https://example.com",
            service_account_email="service@example.com",
            is_active=False
        )
        assert integration.is_active is False
