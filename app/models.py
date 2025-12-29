from datetime import datetime
from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, Date, Table, Text, Enum, JSON, BigInteger
from sqlalchemy.schema import UniqueConstraint
from sqlalchemy.orm import relationship
from app.database import Base
import enum as python_enum


class Organization(Base):
    """Organization groups multiple workspaces and makes resources shared"""
    __tablename__ = 'organization'

    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)
    created_by_user_id = Column(Integer, ForeignKey('user.id'), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    workspaces = relationship('Workspace', back_populates='organization', cascade='all, delete-orphan')
    users = relationship('User', back_populates='organization', cascade='all, delete-orphan', foreign_keys='User.organization_id')
    teams = relationship('Team', back_populates='organization', cascade='all, delete-orphan')
    incidents = relationship('Incident', back_populates='organization', cascade='all, delete-orphan')
    escalations = relationship('Escalation', back_populates='organization', cascade='all, delete-orphan')


class Workspace(Base):
    """Multi-workspace support for data isolation"""
    __tablename__ = 'workspace'

    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)  # Display name
    workspace_type = Column(String, nullable=False)  # 'telegram' or 'slack'
    external_id = Column(String, nullable=False, index=True)  # chat_id or workspace_id
    organization_id = Column(Integer, ForeignKey('organization.id'), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    organization = relationship('Organization', back_populates='workspaces')
    chat_channels = relationship('ChatChannel', back_populates='workspace', cascade='all, delete-orphan')
    users = relationship('User', back_populates='workspace', cascade='all, delete-orphan')
    teams = relationship('Team', back_populates='workspace', cascade='all, delete-orphan')
    admin_logs = relationship('AdminLog', back_populates='workspace', cascade='all, delete-orphan')
    incidents = relationship('Incident', back_populates='workspace', cascade='all, delete-orphan')
    google_calendar_integration = relationship('GoogleCalendarIntegration', back_populates='workspace', uselist=False, cascade='all, delete-orphan')

    __table_args__ = (
        UniqueConstraint('workspace_type', 'external_id', name='workspace_type_external_id_unique'),
    )


class ChatChannel(Base):
    """Specific chat/channel in a workspace"""
    __tablename__ = 'chat_channel'

    id = Column(Integer, primary_key=True)
    workspace_id = Column(Integer, ForeignKey('workspace.id'), nullable=False, index=True)
    messenger = Column(String, nullable=False)  # 'telegram' or 'slack'
    external_id = Column(String, nullable=False)  # chat_id or channel_id
    display_name = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    workspace = relationship('Workspace', back_populates='chat_channels')

    __table_args__ = (
        UniqueConstraint('workspace_id', 'external_id', name='chat_channel_workspace_external_id_unique'),
    )


# Association table for many-to-many team members
team_members = Table(
    'team_members',
    Base.metadata,
    Column('user_id', Integer, ForeignKey('user.id'), primary_key=True),
    Column('team_id', Integer, ForeignKey('team.id'), primary_key=True),
)


class UserAccount(Base):
    """Multiple login methods for a single user across different workspaces"""
    __tablename__ = 'user_account'

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('user.id'), nullable=False, index=True)
    workspace_id = Column(Integer, ForeignKey('workspace.id'), nullable=True, index=True)
    provider = Column(String, nullable=False)  # 'slack' or 'telegram'
    provider_id = Column(String, nullable=False)  # slack_user_id or telegram_id
    username = Column(String, nullable=True)  # slack username or telegram username
    account_email = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    user = relationship('User', back_populates='user_accounts')
    workspace = relationship('Workspace')

    __table_args__ = (
        UniqueConstraint('provider_id', 'workspace_id', name='user_account_provider_id_workspace_id_unique'),
    )


class User(Base):
    __tablename__ = 'user'

    id = Column(Integer, primary_key=True)
    workspace_id = Column(Integer, ForeignKey('workspace.id'), nullable=False, index=True)
    organization_id = Column(Integer, ForeignKey('organization.id'), nullable=True)
    # Removed provider-specific fields
    # telegram_id = Column(BigInteger, nullable=True, index=True)
    # telegram_username = Column(String, nullable=True, index=True)
    # slack_user_id = Column(String, nullable=True, index=True)
    
    username = Column(String, nullable=True, index=True)

    first_name = Column(String, nullable=True)
    last_name = Column(String, nullable=True)
    
    # display_name restored as Column
    display_name = Column(String, nullable=True) 

    is_admin = Column(Boolean, default=False)
    is_superadmin = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    workspace = relationship('Workspace', back_populates='users')
    organization = relationship('Organization', back_populates='users', foreign_keys=[organization_id])
    user_accounts = relationship('UserAccount', back_populates='user', cascade='all, delete-orphan', lazy='selectin')
    teams = relationship('Team', secondary=team_members, back_populates='members')
    led_teams = relationship('Team', back_populates='team_lead_user', foreign_keys='Team.team_lead_id')
    schedules = relationship('Schedule', back_populates='user')
    escalation_as_cto = relationship('Escalation', back_populates='cto_user', foreign_keys='Escalation.cto_id')
    admin_logs_by_admin = relationship('AdminLog', back_populates='admin_user', foreign_keys='AdminLog.admin_user_id')
    admin_logs_by_target = relationship('AdminLog', back_populates='target_user', foreign_keys='AdminLog.target_user_id')

    __table_args__ = (
        # Unique constraints removed as fields were removed
    )

    @property
    def telegram_id(self):
        """Retrieve telegram_id from linked UserAccounts"""
        if self.user_accounts:
            for account in self.user_accounts:
                if account.provider == 'telegram':
                    try:
                        return int(account.provider_id)
                    except (ValueError, TypeError):
                        return None
        return None

    @property
    def telegram_username(self):
        """Retrieve telegram_username from linked UserAccounts or fallback to generic username"""
        if self.user_accounts:
            for account in self.user_accounts:
                if account.provider == 'telegram':
                    return account.username
        return self.username

    @property
    def slack_user_id(self):
        """Retrieve slack_user_id from linked UserAccounts"""
        if self.user_accounts:
            for account in self.user_accounts:
                if account.provider == 'slack':
                    return account.provider_id
        return None


class Team(Base):
    __tablename__ = 'team'

    id = Column(Integer, primary_key=True)
    workspace_id = Column(Integer, ForeignKey('workspace.id'), nullable=False, index=True)
    organization_id = Column(Integer, ForeignKey('organization.id'), nullable=True)
    name = Column(String, nullable=False, index=True)
    display_name = Column(String, nullable=False)
    has_shifts = Column(Boolean, default=False)
    team_lead_id = Column(Integer, ForeignKey('user.id'), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    workspace = relationship('Workspace', back_populates='teams')
    organization = relationship('Organization', back_populates='teams')
    workspace = relationship('Workspace', back_populates='teams', lazy='selectin')
    organization = relationship('Organization', back_populates='teams', lazy='selectin')
    members = relationship('User', secondary=team_members, back_populates='teams', lazy='selectin')
    team_lead_user = relationship('User', back_populates='led_teams', foreign_keys=[team_lead_id], lazy='selectin')
    schedules = relationship('Schedule', back_populates='team', cascade='all, delete-orphan')
    escalations = relationship('Escalation', back_populates='team', cascade='all, delete-orphan')
    rotation_config = relationship('RotationConfig', back_populates='team', cascade='all, delete-orphan', uselist=False, lazy='selectin')

    __table_args__ = (
        UniqueConstraint('workspace_id', 'name', name='team_workspace_name_unique'),
    )


class RotationConfig(Base):
    """Configuration for automatic duty rotation per team"""
    __tablename__ = 'rotation_config'

    id = Column(Integer, primary_key=True)
    team_id = Column(Integer, ForeignKey('team.id'), nullable=False, unique=True)
    enabled = Column(Boolean, default=False)
    member_ids = Column(JSON, nullable=False)  # Ordered list of user IDs for rotation
    last_assigned_user_id = Column(Integer, ForeignKey('user.id'), nullable=True)
    last_assigned_date = Column(Date, nullable=True)
    skip_unavailable = Column(Boolean, default=False)  # Skip users on vacation (future feature)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    team = relationship('Team', back_populates='rotation_config')
    last_assigned_user = relationship('User', foreign_keys=[last_assigned_user_id])


class Schedule(Base):
    """Duty schedule for all teams (both regular and with shifts)"""
    __tablename__ = 'schedule'

    id = Column(Integer, primary_key=True)
    team_id = Column(Integer, ForeignKey('team.id'), nullable=False, index=True)
    user_id = Column(Integer, ForeignKey('user.id'), nullable=True)
    date = Column(Date, nullable=False, index=True)
    is_shift = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    team = relationship('Team', back_populates='schedules', lazy='selectin')
    user = relationship('User', back_populates='schedules', lazy='selectin')

    __table_args__ = (
        UniqueConstraint("team_id", "user_id", "date", name="schedule_team_user_date_unique"),
    )



class EscalationLevelEnum(python_enum.Enum):
    LEVEL1 = 'level1'  # Team lead
    LEVEL2 = 'level2'  # CTO


class Escalation(Base):
    """Escalation configuration"""
    __tablename__ = 'escalation'

    id = Column(Integer, primary_key=True)
    team_id = Column(Integer, ForeignKey('team.id'), nullable=True, index=True)  # NULL for global CTO
    organization_id = Column(Integer, ForeignKey('organization.id'), nullable=True)
    cto_id = Column(Integer, ForeignKey('user.id'), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    team = relationship('Team', back_populates='escalations')
    organization = relationship('Organization', back_populates='escalations')
    cto_user = relationship('User', back_populates='escalation_as_cto', foreign_keys=[cto_id], lazy='joined')


class EscalationEvent(Base):
    """Track escalation events and auto-escalation"""
    __tablename__ = 'escalation_event'

    id = Column(Integer, primary_key=True)
    team_id = Column(Integer, ForeignKey('team.id'), nullable=False, index=True)
    messenger = Column(String, nullable=False)  # 'telegram' or 'slack'
    initiated_at = Column(DateTime, default=datetime.utcnow)
    acknowledged_at = Column(DateTime, nullable=True)
    escalated_to_level2_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    team = relationship('Team')


class AdminLog(Base):
    """Track admin actions for audit trail"""
    __tablename__ = 'admin_log'

    id = Column(Integer, primary_key=True)
    workspace_id = Column(Integer, ForeignKey('workspace.id'), nullable=False, index=True)
    admin_user_id = Column(Integer, ForeignKey('user.id'), nullable=False, index=True)
    action = Column(String, nullable=False)  # e.g., "added_admin", "removed_admin", "changed_schedule"
    target_user_id = Column(Integer, ForeignKey('user.id'), nullable=True)  # Who was affected
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)
    details = Column(Text, nullable=True)  # JSON with change details

    # Relationships
    workspace = relationship('Workspace', back_populates='admin_logs')
    admin_user = relationship('User', back_populates='admin_logs_by_admin', foreign_keys=[admin_user_id])
    target_user = relationship('User', back_populates='admin_logs_by_target', foreign_keys=[target_user_id])


class DutyStats(Base):
    """Monthly duty statistics per user and team"""
    __tablename__ = 'duty_stats'

    id = Column(Integer, primary_key=True)
    workspace_id = Column(Integer, ForeignKey('workspace.id'), nullable=False, index=True)
    team_id = Column(Integer, ForeignKey('team.id'), nullable=False, index=True)
    user_id = Column(Integer, ForeignKey('user.id'), nullable=False, index=True)
    year = Column(Integer, nullable=False)  # Year (e.g., 2024)
    month = Column(Integer, nullable=False)  # Month (1-12)
    duty_days = Column(Integer, default=0)  # Number of days assigned to duties
    shift_days = Column(Integer, default=0)  # Number of days assigned to shifts
    hours_worked = Column(Integer, nullable=True)  # Optional hours worked
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    workspace = relationship('Workspace')
    team = relationship('Team')
    user = relationship('User')

    __table_args__ = (
        UniqueConstraint('workspace_id', 'team_id', 'user_id', 'year', 'month', name='duty_stats_workspace_team_user_year_month_unique'),
    )


class Incident(Base):
    """Incident tracking with start and end times"""
    __tablename__ = 'incident'

    id = Column(Integer, primary_key=True)
    workspace_id = Column(Integer, ForeignKey('workspace.id'), nullable=False, index=True)
    organization_id = Column(Integer, ForeignKey('organization.id'), nullable=True)
    name = Column(String, nullable=False)
    status = Column(Enum('active', 'resolved', name='incident_status_enum'), default='active', nullable=False)
    start_time = Column(DateTime, nullable=False, index=True)
    end_time = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    workspace = relationship('Workspace')
    organization = relationship('Organization', back_populates='incidents')


# Association table for Google Calendar Teams
google_calendar_teams = Table(
    'google_calendar_teams',
    Base.metadata,
    Column('integration_id', Integer, ForeignKey('google_calendar_integration.id', ondelete='CASCADE'), primary_key=True),
    Column('team_id', Integer, ForeignKey('team.id', ondelete='CASCADE'), primary_key=True),
)


class GoogleCalendarIntegration(Base):
    """Google Calendar integration for workspace"""
    __tablename__ = 'google_calendar_integration'

    id = Column(Integer, primary_key=True)
    workspace_id = Column(Integer, ForeignKey('workspace.id'), nullable=False, index=True)

    # team_id removed in favor of M2M relationship

    # Encrypted Service Account key
    service_account_key_encrypted = Column(Text, nullable=False)

    # Google Calendar information
    google_calendar_id = Column(String, nullable=False, unique=True, index=True)
    public_calendar_url = Column(String, nullable=False)

    # Status
    is_active = Column(Boolean, default=True)
    last_sync_at = Column(DateTime, nullable=True)
    service_account_email = Column(String, nullable=False)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    workspace = relationship('Workspace', back_populates='google_calendar_integration')
