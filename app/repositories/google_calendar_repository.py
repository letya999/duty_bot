"""Repository for GoogleCalendarIntegration model."""

from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from app.models import GoogleCalendarIntegration
from app.repositories.base_repository import BaseRepository


class GoogleCalendarRepository(BaseRepository[GoogleCalendarIntegration]):
    """Repository for Google Calendar integration operations."""

    def __init__(self, db: AsyncSession):
        super().__init__(db, GoogleCalendarIntegration)

    async def get_by_workspace(self, workspace_id: int) -> Optional[GoogleCalendarIntegration]:
        """Get Google Calendar integration for workspace."""
        stmt = select(GoogleCalendarIntegration).where(
            GoogleCalendarIntegration.workspace_id == workspace_id
        )
        result = await self.db.execute(stmt)
        return result.scalars().first()

    async def get_by_calendar_id(self, calendar_id: str) -> Optional[GoogleCalendarIntegration]:
        """Get Google Calendar integration by Google Calendar ID."""
        stmt = select(GoogleCalendarIntegration).where(
            GoogleCalendarIntegration.google_calendar_id == calendar_id
        )
        result = await self.db.execute(stmt)
        return result.scalars().first()
