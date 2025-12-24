"""Repository for Workspace model."""

from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from app.models import Workspace
from app.repositories.base_repository import BaseRepository


class WorkspaceRepository(BaseRepository[Workspace]):
    """Repository for Workspace operations."""

    def __init__(self, db: AsyncSession):
        super().__init__(db, Workspace)

    async def get_by_external_id(self, workspace_type: str, external_id: str) -> Optional[Workspace]:
        """Get workspace by type and external ID."""
        stmt = select(Workspace).where(
            Workspace.workspace_type == workspace_type,
            Workspace.external_id == external_id
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_or_create_telegram(self, chat_id: str, name: str) -> Workspace:
        """Get or create Telegram workspace."""
        workspace = await self.get_by_external_id('telegram', chat_id)
        if workspace:
            return workspace
        return await self.create({
            'name': name,
            'workspace_type': 'telegram',
            'external_id': chat_id
        })

    async def get_or_create_slack(self, workspace_id: str, name: str) -> Workspace:
        """Get or create Slack workspace."""
        workspace = await self.get_by_external_id('slack', workspace_id)
        if workspace:
            return workspace
        return await self.create({
            'name': name,
            'workspace_type': 'slack',
            'external_id': workspace_id
        })
