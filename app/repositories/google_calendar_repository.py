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

    async def list_by_workspace(self, workspace_id: int) -> list[GoogleCalendarIntegration]:
        """Get all Google Calendar integrations for workspace."""
        from sqlalchemy.orm import selectinload
        stmt = select(GoogleCalendarIntegration).where(
            GoogleCalendarIntegration.workspace_id == workspace_id
        ).options(selectinload(GoogleCalendarIntegration.teams))
        result = await self.db.execute(stmt)
        return result.scalars().all()

    async def add_teams(self, integration: GoogleCalendarIntegration, teams: list) -> GoogleCalendarIntegration:
        """Add teams to integration."""
        # Re-fetch with relationship loaded to avoid implicit IO error
        from sqlalchemy.orm import selectinload
        stmt = select(GoogleCalendarIntegration).where(
            GoogleCalendarIntegration.id == integration.id
        ).options(selectinload(GoogleCalendarIntegration.teams))
        
        result = await self.db.execute(stmt)
        fresh_integration = result.scalars().first()
        
        if fresh_integration:
            fresh_integration.teams.extend(teams)
            await self.db.commit()
            await self.db.refresh(fresh_integration)
            return fresh_integration
        return integration

    async def get_by_calendar_id(self, calendar_id: str) -> Optional[GoogleCalendarIntegration]:
        """Get Google Calendar integration by Google Calendar ID."""
        stmt = select(GoogleCalendarIntegration).where(
            GoogleCalendarIntegration.google_calendar_id == calendar_id
        )
        result = await self.db.execute(stmt)
        return result.scalars().first()
