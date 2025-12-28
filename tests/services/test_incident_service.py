import pytest
from datetime import datetime, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from app.services.incident_service import IncidentService
from app.models import Workspace, Incident
from app.repositories import IncidentRepository


class TestIncidentService:
    """Test IncidentService methods"""

    @pytest.fixture
    async def setup_incident_service(self, db_session: AsyncSession):
        """Setup incident service with dependencies"""
        incident_repo = IncidentRepository(db_session)
        service = IncidentService(incident_repo)
        return service, incident_repo, db_session

    @pytest.fixture
    async def workspace(self, db_session: AsyncSession):
        """Create test workspace"""
        workspace = Workspace(
            name="Test Workspace",
            workspace_type="telegram",
            external_id="123456789"
        )
        db_session.add(workspace)
        await db_session.commit()
        await db_session.refresh(workspace)
        return workspace

    @pytest.mark.asyncio
    async def test_create_incident(self, setup_incident_service, workspace):
        """Test creating a new incident"""
        service, _, _ = setup_incident_service

        incident = await service.create_incident(workspace.id, "Database outage")

        assert incident is not None
        assert incident.name == "Database outage"
        assert incident.workspace_id == workspace.id
        assert incident.status == "active"
        assert incident.start_time is not None

    @pytest.mark.asyncio
    async def test_create_incident_with_different_names(self, setup_incident_service, workspace):
        """Test creating incidents with different names"""
        service, _, _ = setup_incident_service

        incident1 = await service.create_incident(workspace.id, "API failure")
        incident2 = await service.create_incident(workspace.id, "Database slowdown")

        assert incident1.name == "API failure"
        assert incident2.name == "Database slowdown"

    @pytest.mark.asyncio
    async def test_complete_incident_by_id(self, setup_incident_service, workspace):
        """Test completing incident by ID"""
        service, _, _ = setup_incident_service

        incident = await service.create_incident(workspace.id, "Test incident")
        completed = await service.complete_incident(incident_id=incident.id)

        assert completed is not None
        assert completed.id == incident.id
        assert completed.status == "resolved"
        assert completed.end_time is not None

    @pytest.mark.asyncio
    async def test_complete_incident_by_name(self, setup_incident_service, workspace):
        """Test completing incident by name"""
        service, _, _ = setup_incident_service

        incident = await service.create_incident(workspace.id, "Test incident")
        completed = await service.complete_incident(name="Test incident", workspace_id=workspace.id)

        assert completed is not None
        assert completed.id == incident.id
        assert completed.status == "resolved"

    @pytest.mark.asyncio
    async def test_complete_incident_case_insensitive(self, setup_incident_service, workspace):
        """Test completing incident by name is case insensitive"""
        service, _, _ = setup_incident_service

        incident = await service.create_incident(workspace.id, "Database Outage")
        completed = await service.complete_incident(name="database outage", workspace_id=workspace.id)

        assert completed is not None
        assert completed.id == incident.id

    @pytest.mark.asyncio
    async def test_complete_incident_not_found(self, setup_incident_service, workspace):
        """Test completing non-existent incident returns None"""
        service, _, _ = setup_incident_service

        completed = await service.complete_incident(incident_id=99999)
        assert completed is None

    @pytest.mark.asyncio
    async def test_complete_incident_by_name_not_found(self, setup_incident_service, workspace):
        """Test completing incident by non-existent name returns None"""
        service, _, _ = setup_incident_service

        completed = await service.complete_incident(name="nonexistent", workspace_id=workspace.id)
        assert completed is None

    @pytest.mark.asyncio
    async def test_get_active_incidents(self, setup_incident_service, workspace):
        """Test getting all active incidents"""
        service, _, _ = setup_incident_service

        incident1 = await service.create_incident(workspace.id, "Incident 1")
        incident2 = await service.create_incident(workspace.id, "Incident 2")

        active = await service.get_active_incidents(workspace.id)

        assert len(active) == 2
        assert incident1 in active
        assert incident2 in active

    @pytest.mark.asyncio
    async def test_get_active_incidents_excludes_completed(self, setup_incident_service, workspace):
        """Test active incidents excludes resolved ones"""
        service, _, _ = setup_incident_service

        incident1 = await service.create_incident(workspace.id, "Active incident")
        incident2 = await service.create_incident(workspace.id, "Resolved incident")
        await service.complete_incident(incident_id=incident2.id)

        active = await service.get_active_incidents(workspace.id)

        assert len(active) == 1
        assert incident1 in active
        assert incident2 not in active

    @pytest.mark.asyncio
    async def test_get_active_incidents_empty(self, setup_incident_service, workspace):
        """Test getting active incidents when none exist"""
        service, _, _ = setup_incident_service

        active = await service.get_active_incidents(workspace.id)
        assert len(active) == 0

    @pytest.mark.asyncio
    async def test_get_active_incident_by_name(self, setup_incident_service, workspace):
        """Test getting active incident by name"""
        service, _, _ = setup_incident_service

        incident = await service.create_incident(workspace.id, "Test incident")
        found = await service.get_active_incident_by_name(workspace.id, "Test incident")

        assert found is not None
        assert found.id == incident.id

    @pytest.mark.asyncio
    async def test_get_active_incident_by_name_case_insensitive(self, setup_incident_service, workspace):
        """Test getting incident by name is case insensitive"""
        service, _, _ = setup_incident_service

        incident = await service.create_incident(workspace.id, "Database Outage")
        found = await service.get_active_incident_by_name(workspace.id, "database outage")

        assert found is not None
        assert found.id == incident.id

    @pytest.mark.asyncio
    async def test_get_active_incident_by_name_not_found(self, setup_incident_service, workspace):
        """Test getting non-existent active incident by name returns None"""
        service, _, _ = setup_incident_service

        found = await service.get_active_incident_by_name(workspace.id, "nonexistent")
        assert found is None

    @pytest.mark.asyncio
    async def test_get_active_incident_by_name_resolved(self, setup_incident_service, workspace):
        """Test getting resolved incident by name returns None"""
        service, _, _ = setup_incident_service

        incident = await service.create_incident(workspace.id, "Test incident")
        await service.complete_incident(incident_id=incident.id)

        found = await service.get_active_incident_by_name(workspace.id, "Test incident")
        assert found is None

    @pytest.mark.asyncio
    async def test_get_incident(self, setup_incident_service, workspace):
        """Test getting incident by ID"""
        service, _, _ = setup_incident_service

        incident = await service.create_incident(workspace.id, "Test incident")
        retrieved = await service.get_incident(incident.id)

        assert retrieved is not None
        assert retrieved.id == incident.id
        assert retrieved.name == "Test incident"

    @pytest.mark.asyncio
    async def test_get_incident_not_found(self, setup_incident_service, workspace):
        """Test getting non-existent incident returns None"""
        service, _, _ = setup_incident_service

        retrieved = await service.get_incident(99999)
        assert retrieved is None

    @pytest.mark.asyncio
    async def test_get_incidents_by_date_range(self, setup_incident_service, workspace):
        """Test getting incidents by date range"""
        service, _, _ = setup_incident_service

        now = datetime.utcnow()
        past = now - timedelta(days=7)
        future = now + timedelta(days=7)

        incident1 = await service.create_incident(workspace.id, "Recent incident")

        incidents = await service.get_incidents_by_date_range(workspace.id, past, future)

        assert len(incidents) >= 1
        assert incident1 in incidents

    @pytest.mark.asyncio
    async def test_get_incidents_by_date_range_empty(self, setup_incident_service, workspace):
        """Test getting incidents from future date range"""
        service, _, _ = setup_incident_service

        future_start = datetime.utcnow() + timedelta(days=1)
        future_end = datetime.utcnow() + timedelta(days=7)

        incidents = await service.get_incidents_by_date_range(workspace.id, future_start, future_end)

        assert len(incidents) == 0

    @pytest.mark.asyncio
    async def test_delete_incident(self, setup_incident_service, workspace):
        """Test deleting incident"""
        service, _, _ = setup_incident_service

        incident = await service.create_incident(workspace.id, "To be deleted")
        result = await service.delete_incident(incident.id)

        assert result is True

        retrieved = await service.get_incident(incident.id)
        assert retrieved is None

    @pytest.mark.asyncio
    async def test_delete_incident_not_found(self, setup_incident_service, workspace):
        """Test deleting non-existent incident returns False"""
        service, _, _ = setup_incident_service

        result = await service.delete_incident(99999)
        assert result is False
