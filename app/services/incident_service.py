"""Service for incident management."""

from datetime import datetime
from typing import Optional, List
from app.models import Incident
from app.repositories import IncidentRepository


class IncidentService:
    """Service for managing incidents."""

    def __init__(self, incident_repo: IncidentRepository):
        self.incident_repo = incident_repo

    async def create_incident(self, workspace_id: int, name: str) -> Incident:
        """Create new incident."""
        return await self.incident_repo.create({
            'workspace_id': workspace_id,
            'name': name,
            'status': 'active',
            'start_time': datetime.utcnow(),
        })

    async def complete_incident(self, incident_id: int | None = None, name: str | None = None, workspace_id: int | None = None) -> Optional[Incident]:
        """Complete incident and set end time. Can be identified by ID or name."""
        if incident_id:
            return await self.incident_repo.complete_incident(incident_id, datetime.utcnow())
        
        if name and workspace_id:
            active = await self.get_active_incidents(workspace_id)
            for inc in active:
                if inc.name.lower() == name.lower():
                    return await self.incident_repo.complete_incident(inc.id, datetime.utcnow())
        
        return None

    async def get_active_incidents(self, workspace_id: int) -> List[Incident]:
        """Get all active incidents for workspace."""
        return await self.incident_repo.get_active_incidents(workspace_id)

    async def get_active_incident_by_name(self, workspace_id: int, name: str) -> Optional[Incident]:
        """Get active incident by name."""
        active = await self.get_active_incidents(workspace_id)
        for inc in active:
            if inc.name.lower() == name.lower():
                return inc
        return None

    async def get_incident(self, incident_id: int) -> Optional[Incident]:
        """Get incident by ID."""
        return await self.incident_repo.get_by_id(incident_id)

    async def get_incidents_by_date_range(
        self,
        workspace_id: int,
        start_time: datetime,
        end_time: datetime
    ) -> List[Incident]:
        """Get incidents in date range."""
        return await self.incident_repo.get_by_workspace_and_date_range(
            workspace_id,
            start_time,
            end_time
        )

    async def delete_incident(self, incident_id: int) -> bool:
        """Delete incident."""
        return await self.incident_repo.delete(incident_id)
