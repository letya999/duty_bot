"""Repository for Incident model."""

from datetime import datetime
from typing import Optional, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import and_, or_
from app.models import Incident
from app.repositories.base_repository import BaseRepository


class IncidentRepository(BaseRepository[Incident]):
    """Repository for Incident operations."""

    def __init__(self, db: AsyncSession):
        super().__init__(db, Incident)

    async def get_active_incidents(self, workspace_id: int) -> List[Incident]:
        """Get all active incidents for a workspace."""
        stmt = select(Incident).where(
            and_(
                Incident.workspace_id == workspace_id,
                Incident.status == 'active'
            )
        ).order_by(Incident.start_time.desc())
        result = await self.db.execute(stmt)
        return result.scalars().all()

    async def get_by_workspace_and_date_range(
        self,
        workspace_id: int,
        start_time: datetime,
        end_time: datetime
    ) -> List[Incident]:
        """Get incidents in date range for workspace."""
        stmt = select(Incident).where(
            and_(
                Incident.workspace_id == workspace_id,
                Incident.start_time >= start_time,
                or_(
                    Incident.end_time.is_(None),  # Active incidents
                    Incident.end_time <= end_time  # Resolved incidents
                )
            )
        ).order_by(Incident.start_time.desc())
        result = await self.db.execute(stmt)
        return result.scalars().all()

    async def get_resolved_incidents_by_date_range(
        self,
        workspace_id: int,
        start_time: datetime,
        end_time: datetime
    ) -> List[Incident]:
        """Get resolved incidents in date range for workspace."""
        stmt = select(Incident).where(
            and_(
                Incident.workspace_id == workspace_id,
                Incident.status == 'resolved',
                Incident.end_time >= start_time,
                Incident.end_time <= end_time
            )
        ).order_by(Incident.start_time.desc())
        result = await self.db.execute(stmt)
        return result.scalars().all()

    async def complete_incident(self, incident_id: int, end_time: datetime) -> Optional[Incident]:
        """Mark incident as resolved and set end time."""
        incident = await self.get_by_id(incident_id)
        if not incident:
            return None

        incident.status = 'resolved'
        incident.end_time = end_time
        await self.db.commit()
        await self.db.refresh(incident)
        return incident
