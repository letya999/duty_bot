from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, Date, Table, Text, Enum
from sqlalchemy.schema import UniqueConstraint
from sqlalchemy.orm import relationship
from app.database import Base
import enum as python_enum


# Association table for many-to-many team members
team_members = Table(
    'team_members',
    Base.metadata,
    Column('user_id', Integer, ForeignKey('user.id'), primary_key=True),
    Column('team_id', Integer, ForeignKey('team.id'), primary_key=True),
)


class User(Base):
    __tablename__ = 'user'

    id = Column(Integer, primary_key=True)
    telegram_username = Column(String, nullable=True, unique=True, index=True)
    slack_user_id = Column(String, nullable=True, unique=True, index=True)
    display_name = Column(String, nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    # Relationships
    teams = relationship('Team', secondary=team_members, back_populates='members')
    led_teams = relationship('Team', back_populates='team_lead_user', foreign_keys='Team.team_lead_id')
    schedules = relationship('Schedule', back_populates='user')
    shifts = relationship('Shift', secondary='shift_members', back_populates='users')
    escalation_as_cto = relationship('Escalation', back_populates='cto_user', foreign_keys='Escalation.cto_id')


class Team(Base):
    __tablename__ = 'team'

    id = Column(Integer, primary_key=True)
    name = Column(String, unique=True, nullable=False, index=True)
    display_name = Column(String, nullable=False)
    has_shifts = Column(Boolean, default=False)
    team_lead_id = Column(Integer, ForeignKey('user.id'), nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    # Relationships
    members = relationship('User', secondary=team_members, back_populates='teams')
    team_lead_user = relationship('User', back_populates='led_teams', foreign_keys=[team_lead_id])
    schedules = relationship('Schedule', back_populates='team', cascade='all, delete-orphan')
    shifts = relationship('Shift', back_populates='team', cascade='all, delete-orphan')
    escalations = relationship('Escalation', back_populates='team', cascade='all, delete-orphan')


class Schedule(Base):
    """Duty schedule for teams without shifts"""
    __tablename__ = 'schedule'

    id = Column(Integer, primary_key=True)
    team_id = Column(Integer, ForeignKey('team.id'), nullable=False, index=True)
    user_id = Column(Integer, ForeignKey('user.id'), nullable=True)
    date = Column(Date, nullable=False, index=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    # Relationships
    team = relationship('Team', back_populates='schedules')
    user = relationship('User', back_populates='schedules')

    __table_args__ = (
        UniqueConstraint("team_id", "date", name="schedule_team_date_unique"),
    )


# Association table for many-to-many shift members
shift_members = Table(
    'shift_members',
    Base.metadata,
    Column('user_id', Integer, ForeignKey('user.id'), primary_key=True),
    Column('shift_id', Integer, ForeignKey('shift.id'), primary_key=True),
)


class Shift(Base):
    """Shift schedule for teams with shifts"""
    __tablename__ = 'shift'

    id = Column(Integer, primary_key=True)
    team_id = Column(Integer, ForeignKey('team.id'), nullable=False, index=True)
    date = Column(Date, nullable=False, index=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    # Relationships
    team = relationship('Team', back_populates='shifts')
    users = relationship('User', secondary=shift_members, back_populates='shifts')

    __table_args__ = (
        UniqueConstraint("team_id", "date", name="shift_team_date_unique"),
    )


class EscalationLevelEnum(python_enum.Enum):
    LEVEL1 = 'level1'  # Team lead
    LEVEL2 = 'level2'  # CTO


class Escalation(Base):
    """Escalation configuration"""
    __tablename__ = 'escalation'

    id = Column(Integer, primary_key=True)
    team_id = Column(Integer, ForeignKey('team.id'), nullable=True, index=True)  # NULL for global CTO
    cto_id = Column(Integer, ForeignKey('user.id'), nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    # Relationships
    team = relationship('Team', back_populates='escalations')
    cto_user = relationship('User', back_populates='escalation_as_cto', foreign_keys=[cto_id])


class EscalationEvent(Base):
    """Track escalation events and auto-escalation"""
    __tablename__ = 'escalation_event'

    id = Column(Integer, primary_key=True)
    team_id = Column(Integer, ForeignKey('team.id'), nullable=False, index=True)
    messenger = Column(String, nullable=False)  # 'telegram' or 'slack'
    initiated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    acknowledged_at = Column(DateTime, nullable=True)
    escalated_to_level2_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    # Relationships
    team = relationship('Team')
