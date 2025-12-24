"""Repository for AdminLog model."""

from typing import List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from app.models import AdminLog
from app.repositories.base_repository import BaseRepository


class AdminLogRepository(BaseRepository[AdminLog]):
    """Repository for AdminLog (audit trail) operations."""

    def __init__(self, db: AsyncSession):
        super().__init__(db, AdminLog)

    async def list_by_workspace(self, workspace_id: int, limit: int = 100) -> List[AdminLog]:
        """List admin logs for workspace ordered by timestamp descending."""
        stmt = (
            select(AdminLog)
            .where(AdminLog.workspace_id == workspace_id)
            .order_by(AdminLog.timestamp.desc())
            .limit(limit)
        )
        result = await self.db.execute(stmt)
        return result.scalars().all()

    async def list_by_admin(self, workspace_id: int, admin_user_id: int, limit: int = 100) -> List[AdminLog]:
        """List logs for specific admin."""
        stmt = (
            select(AdminLog)
            .where(
                AdminLog.workspace_id == workspace_id,
                AdminLog.admin_user_id == admin_user_id
            )
            .order_by(AdminLog.timestamp.desc())
            .limit(limit)
        )
        result = await self.db.execute(stmt)
        return result.scalars().all()

    async def list_by_target_user(self, workspace_id: int, target_user_id: int, limit: int = 100) -> List[AdminLog]:
        """List logs for specific target user."""
        stmt = (
            select(AdminLog)
            .where(
                AdminLog.workspace_id == workspace_id,
                AdminLog.target_user_id == target_user_id
            )
            .order_by(AdminLog.timestamp.desc())
            .limit(limit)
        )
        result = await self.db.execute(stmt)
        return result.scalars().all()

    async def log_action(self, workspace_id: int, admin_user_id: int, action: str,
                        target_user_id: int = None, details: str = None) -> AdminLog:
        """Create audit log entry."""
        return await self.create({
            'workspace_id': workspace_id,
            'admin_user_id': admin_user_id,
            'action': action,
            'target_user_id': target_user_id,
            'details': details
        })
