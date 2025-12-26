"""Repository layer for centralized database access."""

from app.repositories.base_repository import BaseRepository
from app.repositories.user_repository import UserRepository
from app.repositories.team_repository import TeamRepository
from app.repositories.workspace_repository import WorkspaceRepository
from app.repositories.schedule_repository import ScheduleRepository
from app.repositories.escalation_repository import EscalationRepository
from app.repositories.escalation_event_repository import EscalationEventRepository
from app.repositories.admin_log_repository import AdminLogRepository
from app.repositories.rotation_config_repository import RotationConfigRepository
from app.repositories.duty_stats_repository import DutyStatsRepository
from app.repositories.incident_repository import IncidentRepository
from app.repositories.google_calendar_repository import GoogleCalendarRepository

__all__ = [
    'BaseRepository',
    'UserRepository',
    'TeamRepository',
    'WorkspaceRepository',
    'ScheduleRepository',
    'EscalationRepository',
    'EscalationEventRepository',
    'AdminLogRepository',
    'RotationConfigRepository',
    'DutyStatsRepository',
    'IncidentRepository',
    'GoogleCalendarRepository',
]
