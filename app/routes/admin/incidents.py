"""API endpoints for incident management."""

import logging
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Header
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import (
    get_db,
    get_incident_repository,
    get_user_repository,
    get_current_user,
)
from app.models import User
from app.services.incident_service import IncidentService
from app.services.metrics_service import MetricsService
from app.repositories import IncidentRepository
from app.exceptions import NotFoundError

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/admin/workspaces")


# Schemas
class IncidentCreateRequest(BaseModel):
    name: str


class IncidentResponse(BaseModel):
    id: int
    name: str
    status: str
    start_time: datetime
    end_time: datetime | None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class MetricsResponse(BaseModel):
    mtr: int
    daysWithoutIncidents: int
    totalIncidents: int
    averageIncidentDuration: int
    period: str
    startTime: str
    endTime: str


# Dependencies
async def get_incident_service(
    incident_repo: IncidentRepository = Depends(get_incident_repository),
) -> IncidentService:
    """Get incident service."""
    return IncidentService(incident_repo)


async def get_metrics_service(
    incident_repo: IncidentRepository = Depends(get_incident_repository),
) -> MetricsService:
    """Get metrics service."""
    return MetricsService(incident_repo)


# Routes
@router.post("/{workspace_id}/incidents", response_model=IncidentResponse)
async def create_incident(
    workspace_id: int,
    request: IncidentCreateRequest,
    user: User = Depends(get_current_user),
    incident_service: IncidentService = Depends(get_incident_service),
) -> IncidentResponse:
    """Create new incident."""
    if user.workspace_id != workspace_id:
        raise HTTPException(status_code=403, detail="Access denied")

    incident = await incident_service.create_incident(workspace_id, request.name)
    return IncidentResponse.model_validate(incident)


@router.get("/{workspace_id}/incidents", response_model=list[IncidentResponse])
async def list_incidents(
    workspace_id: int,
    status: str = None,
    user: User = Depends(get_current_user),
    incident_service: IncidentService = Depends(get_incident_service),
    db: AsyncSession = Depends(get_db),
) -> list[IncidentResponse]:
    """List incidents for workspace."""
    if user.workspace_id != workspace_id:
        raise HTTPException(status_code=403, detail="Access denied")

    # Get all incidents in date range (last 30 days)
    end_time = datetime.utcnow()
    start_time = end_time.replace(day=1)  # Start from beginning of month

    incidents = await incident_service.get_incidents_by_date_range(
        workspace_id,
        start_time,
        end_time
    )

    # Filter by status if provided
    if status:
        incidents = [i for i in incidents if i.status == status]

    return [IncidentResponse.model_validate(i) for i in incidents]


@router.get("/{workspace_id}/incidents/{incident_id}", response_model=IncidentResponse)
async def get_incident(
    workspace_id: int,
    incident_id: int,
    user: User = Depends(get_current_user),
    incident_service: IncidentService = Depends(get_incident_service),
) -> IncidentResponse:
    """Get incident details."""
    if user.workspace_id != workspace_id:
        raise HTTPException(status_code=403, detail="Access denied")

    incident = await incident_service.get_incident(incident_id)
    if not incident or incident.workspace_id != workspace_id:
        raise HTTPException(status_code=404, detail="Incident not found")

    return IncidentResponse.model_validate(incident)


@router.patch("/{workspace_id}/incidents/{incident_id}/complete", response_model=IncidentResponse)
async def complete_incident(
    workspace_id: int,
    incident_id: int,
    user: User = Depends(get_current_user),
    incident_service: IncidentService = Depends(get_incident_service),
) -> IncidentResponse:
    """Complete incident by ID."""
    if user.workspace_id != workspace_id:
        raise HTTPException(status_code=403, detail="Access denied")

    incident = await incident_service.get_incident(incident_id)
    if not incident or incident.workspace_id != workspace_id:
        raise HTTPException(status_code=404, detail="Incident not found")

    completed = await incident_service.complete_incident(incident_id=incident_id)
    return IncidentResponse.model_validate(completed)


class IncidentStopRequest(BaseModel):
    name: str


@router.patch("/{workspace_id}/incidents/stop", response_model=IncidentResponse)
async def stop_incident_by_name(
    workspace_id: int,
    request: IncidentStopRequest,
    user: User = Depends(get_current_user),
    incident_service: IncidentService = Depends(get_incident_service),
) -> IncidentResponse:
    """Stop incident by name."""
    if user.workspace_id != workspace_id:
        raise HTTPException(status_code=403, detail="Access denied")

    completed = await incident_service.complete_incident(name=request.name, workspace_id=workspace_id)
    if not completed:
        raise HTTPException(status_code=404, detail=f"Active incident with name '{request.name}' not found")
        
    return IncidentResponse.model_validate(completed)


@router.delete("/{workspace_id}/incidents/{incident_id}")
async def delete_incident(
    workspace_id: int,
    incident_id: int,
    user: User = Depends(get_current_user),
    incident_service: IncidentService = Depends(get_incident_service),
) -> dict:
    """Delete incident."""
    if user.workspace_id != workspace_id:
        raise HTTPException(status_code=403, detail="Access denied")

    incident = await incident_service.get_incident(incident_id)
    if not incident or incident.workspace_id != workspace_id:
        raise HTTPException(status_code=404, detail="Incident not found")

    await incident_service.delete_incident(incident_id)
    return {"deleted": True}


@router.get("/{workspace_id}/incidents/metrics/summary", response_model=MetricsResponse)
async def get_metrics(
    workspace_id: int,
    period: str = "week",
    user: User = Depends(get_current_user),
    metrics_service: MetricsService = Depends(get_metrics_service),
) -> MetricsResponse:
    """Get incident metrics for workspace."""
    if user.workspace_id != workspace_id:
        raise HTTPException(status_code=403, detail="Access denied")

    valid_periods = ['week', 'month', 'quarter', 'year']
    if period not in valid_periods:
        period = 'week'

    metrics = await metrics_service.calculate_metrics(workspace_id, period)
    return MetricsResponse(**metrics)
