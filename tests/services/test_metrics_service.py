import pytest
from datetime import datetime, timedelta
from unittest.mock import AsyncMock
from sqlalchemy.ext.asyncio import AsyncSession
from app.services.metrics_service import MetricsService
from app.repositories.incident_repository import IncidentRepository
from app.models import Workspace, Incident


class TestMetricsService:
    """Test MetricsService for calculating incident metrics"""

    @pytest.fixture
    async def setup_metrics_service(self, db_session: AsyncSession):
        """Setup metrics service with test data"""
        # Create workspace
        workspace = Workspace(
            name="Test Workspace",
            workspace_type="telegram",
            external_id="123456789"
        )
        db_session.add(workspace)
        await db_session.commit()
        await db_session.refresh(workspace)

        # Create repository and service
        incident_repo = IncidentRepository(db_session)
        service = MetricsService(incident_repo)

        return service, workspace, db_session

    @pytest.mark.asyncio
    async def test_calculate_metrics_no_incidents(self, setup_metrics_service):
        """Test calculating metrics when there are no incidents"""
        service, workspace, db_session = setup_metrics_service

        metrics = await service.calculate_metrics(workspace.id, 'week')

        assert metrics is not None
        assert metrics['mtr'] == 0
        assert metrics['totalIncidents'] == 0
        assert metrics['averageIncidentDuration'] == 0
        assert metrics['period'] == 'week'
        assert 'startTime' in metrics
        assert 'endTime' in metrics

    @pytest.mark.asyncio
    async def test_calculate_metrics_with_resolved_incidents(self, setup_metrics_service):
        """Test calculating metrics with resolved incidents"""
        service, workspace, db_session = setup_metrics_service

        # Create resolved incidents with known durations
        now = datetime.utcnow()
        incidents = [
            Incident(
                workspace_id=workspace.id,
                name="Incident 1",
                status="resolved",
                start_time=now - timedelta(hours=2),
                end_time=now - timedelta(hours=1)  # 1 hour duration
            ),
            Incident(
                workspace_id=workspace.id,
                name="Incident 2",
                status="resolved",
                start_time=now - timedelta(hours=5),
                end_time=now - timedelta(hours=2)  # 3 hours duration
            )
        ]
        for incident in incidents:
            db_session.add(incident)
        await db_session.commit()

        metrics = await service.calculate_metrics(workspace.id, 'week')

        assert metrics['totalIncidents'] == 2
        # MTR should be average: (3600 + 10800) / 2 = 7200 seconds
        assert metrics['mtr'] == 7200
        assert metrics['averageIncidentDuration'] == 7200

    @pytest.mark.asyncio
    async def test_calculate_metrics_with_active_incidents(self, setup_metrics_service):
        """Test calculating metrics with active incidents"""
        service, workspace, db_session = setup_metrics_service

        # Create active incident
        now = datetime.utcnow()
        incident = Incident(
            workspace_id=workspace.id,
            name="Active Incident",
            status="active",
            start_time=now - timedelta(hours=1),
            end_time=None
        )
        db_session.add(incident)
        await db_session.commit()

        metrics = await service.calculate_metrics(workspace.id, 'week')

        assert metrics['totalIncidents'] == 1
        assert metrics['mtr'] == 0  # Active incidents don't contribute to MTR
        # Active incident today means 0 consecutive days without incidents
        assert metrics['daysWithoutIncidents'] == 0

    @pytest.mark.asyncio
    async def test_calculate_metrics_days_without_incidents_resolved(self, setup_metrics_service):
        """Test days without incidents calculation with resolved incidents"""
        service, workspace, db_session = setup_metrics_service

        # Create incident resolved 3 days ago
        now = datetime.utcnow()
        incident = Incident(
            workspace_id=workspace.id,
            name="Old Incident",
            status="resolved",
            start_time=now - timedelta(days=5),
            end_time=now - timedelta(days=3)
        )
        db_session.add(incident)
        await db_session.commit()

        metrics = await service.calculate_metrics(workspace.id, 'week')

        # Counting consecutive days without incidents from today backwards:
        # Today: clean, Yesterday: clean, 2 days ago: clean, 3 days ago: INCIDENT -> STOP
        # Result: 3 consecutive incident-free days
        assert metrics['daysWithoutIncidents'] == 3

    @pytest.mark.asyncio
    async def test_calculate_metrics_days_without_incidents_no_incidents(self, setup_metrics_service):
        """Test days without incidents when there are no incidents at all"""
        service, workspace, db_session = setup_metrics_service

        metrics = await service.calculate_metrics(workspace.id, 'week')

        # Should return full period (7 days for week)
        assert metrics['daysWithoutIncidents'] == 7

    @pytest.mark.asyncio
    async def test_calculate_metrics_period_week(self, setup_metrics_service):
        """Test metrics calculation for week period"""
        service, workspace, db_session = setup_metrics_service

        metrics = await service.calculate_metrics(workspace.id, 'week')

        start_time = datetime.fromisoformat(metrics['startTime'])
        end_time = datetime.fromisoformat(metrics['endTime'])
        diff = end_time - start_time

        # Week period should be 7 days
        assert diff.days == 7

    @pytest.mark.asyncio
    async def test_calculate_metrics_period_month(self, setup_metrics_service):
        """Test metrics calculation for month period"""
        service, workspace, db_session = setup_metrics_service

        metrics = await service.calculate_metrics(workspace.id, 'month')

        start_time = datetime.fromisoformat(metrics['startTime'])
        end_time = datetime.fromisoformat(metrics['endTime'])
        diff = end_time - start_time

        # Month period should be 30 days
        assert diff.days == 30
        assert metrics['period'] == 'month'

    @pytest.mark.asyncio
    async def test_calculate_metrics_period_quarter(self, setup_metrics_service):
        """Test metrics calculation for quarter period"""
        service, workspace, db_session = setup_metrics_service

        metrics = await service.calculate_metrics(workspace.id, 'quarter')

        start_time = datetime.fromisoformat(metrics['startTime'])
        end_time = datetime.fromisoformat(metrics['endTime'])
        diff = end_time - start_time

        # Quarter period should be 90 days
        assert diff.days == 90
        assert metrics['period'] == 'quarter'

    @pytest.mark.asyncio
    async def test_calculate_metrics_period_year(self, setup_metrics_service):
        """Test metrics calculation for year period"""
        service, workspace, db_session = setup_metrics_service

        metrics = await service.calculate_metrics(workspace.id, 'year')

        start_time = datetime.fromisoformat(metrics['startTime'])
        end_time = datetime.fromisoformat(metrics['endTime'])
        diff = end_time - start_time

        # Year period should be 365 days
        assert diff.days == 365
        assert metrics['period'] == 'year'

    @pytest.mark.asyncio
    async def test_calculate_metrics_period_invalid_defaults_to_week(self, setup_metrics_service):
        """Test that invalid period defaults to week"""
        service, workspace, db_session = setup_metrics_service

        metrics = await service.calculate_metrics(workspace.id, 'invalid_period')

        start_time = datetime.fromisoformat(metrics['startTime'])
        end_time = datetime.fromisoformat(metrics['endTime'])
        diff = end_time - start_time

        # Should default to week (7 days)
        assert diff.days == 7

    @pytest.mark.asyncio
    async def test_get_period_start_week(self, setup_metrics_service):
        """Test _get_period_start for week"""
        service, workspace, db_session = setup_metrics_service

        end_time = datetime.utcnow()
        start_time = service._get_period_start(end_time, 'week')

        assert (end_time - start_time).days == 7

    @pytest.mark.asyncio
    async def test_get_period_start_month(self, setup_metrics_service):
        """Test _get_period_start for month"""
        service, workspace, db_session = setup_metrics_service

        end_time = datetime.utcnow()
        start_time = service._get_period_start(end_time, 'month')

        assert (end_time - start_time).days == 30

    @pytest.mark.asyncio
    async def test_get_period_start_quarter(self, setup_metrics_service):
        """Test _get_period_start for quarter"""
        service, workspace, db_session = setup_metrics_service

        end_time = datetime.utcnow()
        start_time = service._get_period_start(end_time, 'quarter')

        assert (end_time - start_time).days == 90

    @pytest.mark.asyncio
    async def test_get_period_start_year(self, setup_metrics_service):
        """Test _get_period_start for year"""
        service, workspace, db_session = setup_metrics_service

        end_time = datetime.utcnow()
        start_time = service._get_period_start(end_time, 'year')

        assert (end_time - start_time).days == 365

    @pytest.mark.asyncio
    async def test_calculate_mtr_empty_list(self, setup_metrics_service):
        """Test _calculate_mtr with empty incident list"""
        service, workspace, db_session = setup_metrics_service

        mtr = service._calculate_mtr([])

        assert mtr == 0

    @pytest.mark.asyncio
    async def test_calculate_mtr_single_incident(self, setup_metrics_service, incident_factory):
        """Test _calculate_mtr with single incident"""
        service, workspace, db_session = setup_metrics_service

        start = datetime.utcnow() - timedelta(hours=2)
        end = datetime.utcnow()
        incident = incident_factory(
            workspace_id=workspace.id,
            status="resolved",
            start_time=start,
            end_time=end
        )

        mtr = service._calculate_mtr([incident])

        # Should be 2 hours = 7200 seconds
        expected_duration = int((end - start).total_seconds())
        assert mtr == expected_duration

    @pytest.mark.asyncio
    async def test_calculate_mtr_multiple_incidents(self, setup_metrics_service, incident_factory):
        """Test _calculate_mtr with multiple incidents"""
        service, workspace, db_session = setup_metrics_service

        now = datetime.utcnow()
        incidents = [
            incident_factory(
                workspace_id=workspace.id,
                status="resolved",
                start_time=now - timedelta(hours=2),
                end_time=now - timedelta(hours=1)  # 1 hour = 3600 seconds
            ),
            incident_factory(
                workspace_id=workspace.id,
                status="resolved",
                start_time=now - timedelta(hours=5),
                end_time=now - timedelta(hours=2)  # 3 hours = 10800 seconds
            )
        ]

        mtr = service._calculate_mtr(incidents)

        # Average: (3600 + 10800) / 2 = 7200
        assert mtr == 7200

    @pytest.mark.asyncio
    async def test_calculate_mtr_incident_without_end_time(self, setup_metrics_service, incident_factory):
        """Test _calculate_mtr with incidents without end_time"""
        service, workspace, db_session = setup_metrics_service

        now = datetime.utcnow()
        incidents = [
            incident_factory(
                workspace_id=workspace.id,
                status="active",
                start_time=now - timedelta(hours=1),
                end_time=None  # No end time
            ),
            incident_factory(
                workspace_id=workspace.id,
                status="resolved",
                start_time=now - timedelta(hours=2),
                end_time=now - timedelta(hours=1)  # 1 hour = 3600 seconds
            )
        ]

        mtr = service._calculate_mtr(incidents)

        # MTR divides total duration by total incident count
        # Only the resolved incident contributes 3600 seconds, divided by 2 incidents = 1800
        assert mtr == 1800

    @pytest.mark.asyncio
    async def test_calculate_avg_duration(self, setup_metrics_service, incident_factory):
        """Test _calculate_avg_duration"""
        service, workspace, db_session = setup_metrics_service

        now = datetime.utcnow()
        incidents = [
            incident_factory(
                workspace_id=workspace.id,
                status="resolved",
                start_time=now - timedelta(hours=2),
                end_time=now - timedelta(hours=1)
            )
        ]

        avg_duration = service._calculate_avg_duration(incidents)

        # Should be same as MTR
        assert avg_duration == service._calculate_mtr(incidents)

    @pytest.mark.asyncio
    async def test_calculate_days_without_incidents_with_active(self, setup_metrics_service, incident_factory):
        """Test _calculate_days_without_incidents with active incidents"""
        service, workspace, db_session = setup_metrics_service

        now = datetime.utcnow()
        start_time = now - timedelta(days=7)
        incidents = [
            incident_factory(
                workspace_id=workspace.id,
                status="active",
                start_time=now - timedelta(hours=1),
                end_time=None
            )
        ]

        days = await service._calculate_days_without_incidents(incidents, start_time, now)

        # Active incident today means we encounter it on first day = 0 consecutive days without incidents
        assert days == 0

    @pytest.mark.asyncio
    async def test_calculate_days_without_incidents_no_incidents(self, setup_metrics_service):
        """Test _calculate_days_without_incidents with no incidents"""
        service, workspace, db_session = setup_metrics_service

        now = datetime.utcnow()
        start_time = now - timedelta(days=7)

        days = await service._calculate_days_without_incidents([], start_time, now)

        # Should return total days in period
        assert days == 7

    @pytest.mark.asyncio
    async def test_calculate_days_without_incidents_resolved(self, setup_metrics_service, incident_factory):
        """Test _calculate_days_without_incidents with resolved incidents"""
        service, workspace, db_session = setup_metrics_service

        now = datetime.utcnow()
        start_time = now - timedelta(days=7)
        incidents = [
            incident_factory(
                workspace_id=workspace.id,
                status="resolved",
                start_time=now - timedelta(days=5),
                end_time=now - timedelta(days=3)
            )
        ]

        days = await service._calculate_days_without_incidents(incidents, start_time, now)

        # Counting backwards from today: today (clean), yesterday (clean), 2 days ago (clean),
        # 3 days ago (INCIDENT) -> STOP
        # Result: 3 consecutive days without incidents
        assert days == 3

    @pytest.mark.asyncio
    async def test_calculate_days_without_incidents_multiple_resolved(self, setup_metrics_service, incident_factory):
        """Test _calculate_days_without_incidents with multiple incidents"""
        service, workspace, db_session = setup_metrics_service

        now = datetime.utcnow()
        start_time = now - timedelta(days=7)
        incidents = [
            incident_factory(
                workspace_id=workspace.id,
                status="resolved",
                start_time=now - timedelta(days=6),
                end_time=now - timedelta(days=5)
            ),
            incident_factory(
                workspace_id=workspace.id,
                status="resolved",
                start_time=now - timedelta(days=3),
                end_time=now - timedelta(days=2)
            )
        ]

        days = await service._calculate_days_without_incidents(incidents, start_time, now)

        # Counting backwards from today: today (clean), yesterday (clean),
        # 2 days ago (INCIDENT) -> STOP
        # Result: 2 consecutive days without incidents
        assert days == 2

    @pytest.mark.asyncio
    async def test_calculate_metrics_complete_workflow(self, setup_metrics_service):
        """Test complete metrics calculation workflow"""
        service, workspace, db_session = setup_metrics_service

        now = datetime.utcnow()

        # Create a mix of incidents
        incidents = [
            # Resolved incident 1 (duration: 1 hour)
            Incident(
                workspace_id=workspace.id,
                name="Incident 1",
                status="resolved",
                start_time=now - timedelta(days=5, hours=2),
                end_time=now - timedelta(days=5, hours=1)
            ),
            # Resolved incident 2 (duration: 2 hours)
            Incident(
                workspace_id=workspace.id,
                name="Incident 2",
                status="resolved",
                start_time=now - timedelta(days=3, hours=2),
                end_time=now - timedelta(days=3)
            ),
            # Resolved incident 3 (duration: 3 hours)
            Incident(
                workspace_id=workspace.id,
                name="Incident 3",
                status="resolved",
                start_time=now - timedelta(days=1, hours=3),
                end_time=now - timedelta(days=1)
            ),
        ]
        for incident in incidents:
            db_session.add(incident)
        await db_session.commit()

        metrics = await service.calculate_metrics(workspace.id, 'week')

        # Verify all metrics are calculated correctly
        assert metrics['totalIncidents'] == 3
        assert metrics['mtr'] > 0  # Should have positive MTR
        assert metrics['averageIncidentDuration'] == metrics['mtr']
        assert metrics['daysWithoutIncidents'] >= 0
        assert metrics['period'] == 'week'
        assert 'startTime' in metrics
        assert 'endTime' in metrics
