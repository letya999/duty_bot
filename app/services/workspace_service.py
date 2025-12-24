"""Service for Workspace operations."""

from app.models import Workspace
from app.repositories import WorkspaceRepository


class WorkspaceService:
    def __init__(self, workspace_repo: WorkspaceRepository):
        self.workspace_repo = workspace_repo

    async def get_workspace_by_id(self, workspace_id: int) -> Workspace | None:
        """Get workspace by ID."""
        return await self.workspace_repo.get_by_id(workspace_id)

    async def get_or_create_telegram_workspace(self, chat_id: str, name: str) -> Workspace:
        """Get or create Telegram workspace."""
        return await self.workspace_repo.get_or_create_telegram(chat_id, name)

    async def get_or_create_slack_workspace(self, workspace_id: str, name: str) -> Workspace:
        """Get or create Slack workspace."""
        return await self.workspace_repo.get_or_create_slack(workspace_id, name)

    async def get_by_external_id(self, workspace_type: str, external_id: str) -> Workspace | None:
        """Get workspace by type and external ID."""
        return await self.workspace_repo.get_by_external_id(workspace_type, external_id)
