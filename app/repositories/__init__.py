"""Repository layer for centralized database access."""

from app.repositories.base_repository import BaseRepository
from app.repositories.user_repository import UserRepository
from app.repositories.team_repository import TeamRepository
from app.repositories.workspace_repository import WorkspaceRepository
from app.repositories.schedule_repository import ScheduleRepository
from app.repositories.shift_repository import ShiftRepository
from app.repositories.escalation_repository import EscalationRepository
from app.repositories.admin_log_repository import AdminLogRepository
from app.repositories.rotation_config_repository import RotationConfigRepository

__all__ = [
    'BaseRepository',
    'UserRepository',
    'TeamRepository',
    'WorkspaceRepository',
    'ScheduleRepository',
    'ShiftRepository',
    'EscalationRepository',
    'AdminLogRepository',
    'RotationConfigRepository',
]
