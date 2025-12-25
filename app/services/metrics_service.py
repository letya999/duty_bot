"""Service for calculating incident metrics."""

from datetime import datetime, timedelta
from typing import Dict, List
from app.models import Incident
from app.repositories import IncidentRepository


class MetricsService:
    """Service for calculating incident metrics."""

    def __init__(self, incident_repo: IncidentRepository):
        self.incident_repo = incident_repo

    async def calculate_metrics(
        self,
        workspace_id: int,
        period: str = 'week'
    ) -> Dict:
        """Calculate metrics for given period."""
        end_time = datetime.utcnow()
        start_time = self._get_period_start(end_time, period)

        # Get resolved incidents in period
        resolved_incidents = await self.incident_repo.get_resolved_incidents_by_date_range(
            workspace_id,
            start_time,
            end_time
        )

        # Get all incidents in period (for total count)
        all_incidents = await self.incident_repo.get_by_workspace_and_date_range(
            workspace_id,
            start_time,
            end_time
        )

        # Calculate metrics
        mtr = self._calculate_mtr(resolved_incidents)
        avg_duration = self._calculate_avg_duration(resolved_incidents)
        days_without_incidents = await self._calculate_days_without_incidents(
            all_incidents,
            start_time,
            end_time
        )

        return {
            'mtr': mtr,  # in seconds
            'daysWithoutIncidents': days_without_incidents,
            'totalIncidents': len(all_incidents),
            'averageIncidentDuration': avg_duration,  # in seconds
            'period': period,
            'startTime': start_time.isoformat(),
            'endTime': end_time.isoformat(),
        }

    def _get_period_start(self, end_time: datetime, period: str) -> datetime:
        """Get start time based on period."""
        if period == 'week':
            return end_time - timedelta(days=7)
        elif period == 'month':
            return end_time - timedelta(days=30)
        elif period == 'quarter':
            return end_time - timedelta(days=90)
        elif period == 'year':
            return end_time - timedelta(days=365)
        else:
            return end_time - timedelta(days=7)

    def _calculate_mtr(self, incidents: List[Incident]) -> int:
        """Calculate Mean Time to Resolution in seconds."""
        if not incidents:
            return 0

        total_duration = 0
        for incident in incidents:
            if incident.end_time and incident.start_time:
                duration = (incident.end_time - incident.start_time).total_seconds()
                total_duration += duration

        return int(total_duration / len(incidents)) if incidents else 0

    def _calculate_avg_duration(self, incidents: List[Incident]) -> int:
        """Calculate average incident duration in seconds."""
        return self._calculate_mtr(incidents)  # Same calculation

    async def _calculate_days_without_incidents(
        self,
        incidents: List[Incident],
        start_time: datetime,
        end_time: datetime
    ) -> int:
        """Calculate number of days without any incidents."""
        # Get all dates in period that have incidents
        incident_dates = set()
        for incident in incidents:
            # For each day the incident spans
            current_date = incident.start_time.date()
            end_date = (incident.end_time or end_time).date()

            while current_date <= end_date:
                incident_dates.add(current_date)
                current_date += timedelta(days=1)

        # Count days without incidents
        days_without = 0
        current_date = start_time.date()
        end_date = end_time.date()

        while current_date <= end_date:
            if current_date not in incident_dates:
                days_without += 1
            current_date += timedelta(days=1)

        return days_without
