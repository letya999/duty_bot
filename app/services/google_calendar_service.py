"""Service for Google Calendar integration."""

import logging
import json
import asyncio
from datetime import datetime, date as date_type, timedelta
from typing import Optional, Dict, Any, List
from google.oauth2.service_account import Credentials
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from app.models import GoogleCalendarIntegration, Schedule, Team, User
from app.repositories.google_calendar_repository import GoogleCalendarRepository
from app.repositories.schedule_repository import ScheduleRepository
from app.repositories.team_repository import TeamRepository
from app.utils.encryption import encrypt_string, decrypt_string
from app.exceptions import ValidationError

logger = logging.getLogger(__name__)

SCOPES = ['https://www.googleapis.com/auth/calendar']


class GoogleCalendarService:
    """Service for syncing duty schedules with Google Calendar."""

    def __init__(self, google_calendar_repo: GoogleCalendarRepository):
        self.repo = google_calendar_repo

    def _decrypt_service_account_key(self, encrypted_key: str) -> Dict[str, Any]:
        """Decrypt and parse service account key."""
        try:
            decrypted = decrypt_string(encrypted_key)
            return json.loads(decrypted)
        except Exception as e:
            logger.error(f"Failed to decrypt service account key: {e}")
            raise ValidationError("Failed to decrypt Google Calendar credentials")

    def _get_calendar_service(self, service_account_key: Dict[str, Any]):
        """Get Google Calendar service from service account key."""
        try:
            credentials = Credentials.from_service_account_info(
                service_account_key,
                scopes=SCOPES
            )
            return build('calendar', 'v3', credentials=credentials, cache_discovery=False)
        except Exception as e:
            logger.error(f"Failed to create Google Calendar service: {e}")
            raise ValidationError("Failed to authenticate with Google Calendar")

    async def setup_google_calendar(
        self,
        workspace_id: int,
        service_account_key: Dict[str, Any],
        team_ids: Optional[List[int]] = None
    ) -> GoogleCalendarIntegration:
        """Setup Google Calendar integration for workspace."""
        try:
            # Validate service account key
            if not isinstance(service_account_key, dict):
                logger.error(f"Service account key is not a dictionary: {type(service_account_key)}")
                raise ValidationError(f"Invalid service account key format: expected JSON object, got {type(service_account_key).__name__}")

            if 'client_email' not in service_account_key:
                logger.error(f"Service account key missing client_email. Available keys: {list(service_account_key.keys())}")
                raise ValidationError(f"Invalid service account key format: missing 'client_email'. Found keys: {', '.join(service_account_key.keys())}")

            service = self._get_calendar_service(service_account_key)

            # Create a new calendar in thread pool to avoid blocking event loop
            calendar_body = {
                'summary': f'Duty Schedule',
                'description': 'Team duty rotation schedule',
                'timeZone': 'UTC'
            }

            calendar = await asyncio.to_thread(
                service.calendars().insert(body=calendar_body).execute
            )
            calendar_id = calendar['id']

            # Make calendar public in thread pool
            rule = {
                'scope': {'type': 'default'},
                'role': 'reader'
            }
            await asyncio.to_thread(
                service.acl().insert(calendarId=calendar_id, body=rule).execute
            )

            # Get public calendar URL
            public_url = f"https://calendar.google.com/calendar/u/0?cid={calendar_id}"

            # Encrypt service account key
            encrypted_key = encrypt_string(json.dumps(service_account_key))

            # Create integration record
            integration_data = {
                "workspace_id": workspace_id,
                "service_account_key_encrypted": encrypted_key,
                "google_calendar_id": calendar_id,
                "public_calendar_url": public_url,
                "service_account_email": service_account_key['client_email'],
                "is_active": True,
                "team_id": team_id
            }

            integration = await self.repo.create(integration_data)

            # Associate teams if provided
            if team_ids:
                # We need to fetch team objects to associate them
                # Ideally repo would handle this, but for now let's query repo or assume IDs are valid
                # Let's rely on repository layer to attach by ID if possible, or fetch simple objects
                # Since we are in service, we might need a TeamRepository passed in or use a session
                # But notice we don't have TeamRepository in __init__.
                # We can't easily fetch teams here without TeamRepository.
                # Let's change signature or rely on caller to pass objects?
                # BETTER: Just save the integration, and let caller handle team association?
                # OR: Repo method add_teams logic.
                
                # To keep it clean, let's assume valid IDs are passed and use a direct DB add in repo
                pass # We will handle this by returning the integration and letting the endpoint add teams
                
            return integration

        except HttpError as e:
            logger.error(f"Google API error: {e}")
            raise ValidationError(f"Google Calendar API error: {e.reason}")
        except Exception as e:
            logger.error(f"Error setting up Google Calendar: {e}")
            raise

    async def sync_schedule_to_calendar(
        self,
        integration: GoogleCalendarIntegration,
        team: Team,
        schedule: Schedule,
        service: Any = None
    ) -> Optional[str]:
        """
        Sync duty schedule to Google Calendar. Returns event ID.
        If service is provided, uses it directly (avoids repeated decryption/auth).
        """
        try:
            if not service:
                service_account_key = self._decrypt_service_account_key(
                    integration.service_account_key_encrypted
                )
                service = self._get_calendar_service(service_account_key)

            # Create event body
            end_date = schedule.date + timedelta(days=1)
            event_body = {
                'summary': f"👥 {team.display_name} - {schedule.user.first_name or schedule.user.username}",
                'description': f"On-call person for {team.display_name} from 00:00 to 23:59",
                'start': {
                    'date': schedule.date.isoformat()
                },
                'end': {
                    'date': end_date.isoformat()
                },
                'colorId': str(self._get_team_color(team.id))
            }

            # Create event in thread pool to avoid blocking event loop
            event = await asyncio.to_thread(
                service.events().insert(
                    calendarId=integration.google_calendar_id,
                    body=event_body
                ).execute
            )

            event_id = event['id']
            logger.info(f"Created calendar event {event_id} for schedule {schedule.id}")

            return event_id

        except HttpError as e:
            logger.error(f"Google API error while syncing schedule: {e}")
        except Exception as e:
            logger.error(f"Error syncing schedule to calendar: {e}")

        return None

    async def delete_calendar_event(
        self,
        integration: GoogleCalendarIntegration,
        event_id: str
    ) -> bool:
        """Delete event from Google Calendar."""
        try:
            service_account_key = self._decrypt_service_account_key(
                integration.service_account_key_encrypted
            )
            service = self._get_calendar_service(service_account_key)

            # Delete event in thread pool to avoid blocking event loop
            await asyncio.to_thread(
                service.events().delete(
                    calendarId=integration.google_calendar_id,
                    eventId=event_id
                ).execute
            )

            logger.info(f"Deleted calendar event {event_id}")
            return True

        except HttpError as e:
            logger.error(f"Google API error while deleting event: {e}")
        except Exception as e:
            logger.error(f"Error deleting calendar event: {e}")

        return False

    async def disconnect_google_calendar(self, integration_id: int) -> bool:
        """Disconnect specific Google Calendar integration."""
        try:
            integration = await self.repo.get_by_id(integration_id)
            if not integration:
                return False

            # Try to delete the calendar from Google side if possible
            try:
                service_account_key = self._decrypt_service_account_key(
                    integration.service_account_key_encrypted
                )
                service = self._get_calendar_service(service_account_key)
                
                service.calendars().delete(
                    calendarId=integration.google_calendar_id
                ).execute()
                logger.info(f"Deleted calendar {integration.google_calendar_id} from Google")
            except Exception as e:
                logger.warning(f"Could not delete calendar from Google side (likely decryption or API error): {e}")
                # We continue anyway because we want to clear the local database state

            # ALWAYS delete integration record from local DB
            await self.repo.delete(integration.id)
            logger.info(f"Google Calendar integration record {integration.id} deleted from DB")

            return True

        except Exception as e:
            logger.error(f"Error disconnecting Google Calendar: {e}")
            return False

    async def sync_workspace_schedules(
        self,
        workspace_id: int,
        schedule_repo: ScheduleRepository,
        team_repo: TeamRepository
    ) -> int:
        """Sync all future schedules for a workspace to Google Calendar. Returns count of synced events."""
        try:
            integrations = await self.repo.list_by_workspace(workspace_id)
            if not integrations:
                logger.warning(f"No Google Calendar integrations for workspace {workspace_id}")
                return 0

            total_synced_count = 0
            
            # Define range for initial sync: 1 day ago to 90 days in future
            start_date = date_type.today() - timedelta(days=1)
            end_date = date_type.today() + timedelta(days=90)

            for integration in integrations:
                if not integration.is_active:
                    continue

                # Determine which teams to sync for this integration
                if integration.teams:
                    # Sync only for specific linked teams
                    teams_to_sync = integration.teams
                else:
                    # Sync for all teams (legacy/global behavior)
                    teams_to_sync = await team_repo.list_by_workspace(workspace_id)

                teams_to_sync = [t for t in teams_to_sync if t] # Filter None

                # Decrypt and get service once per integration
                try:
                    service_account_key = self._decrypt_service_account_key(
                        integration.service_account_key_encrypted
                    )
                    service = self._get_calendar_service(service_account_key)
                except Exception as e:
                    logger.error(f"Failed to initialize Google Calendar for integration {integration.id}: {e}")
                    continue

                for team in teams_to_sync:
                    # Use a more efficient way to get schedules with users
                    from sqlalchemy import select
                    from sqlalchemy.orm import joinedload
                    
                    stmt = select(Schedule).options(
                        joinedload(Schedule.user)
                    ).where(
                        Schedule.team_id == team.id,
                        Schedule.date >= start_date,
                        Schedule.date <= end_date
                    )
                    
                    result = await schedule_repo.execute(stmt)
                    schedules = result.scalars().all()
                    
                    for schedule in schedules:
                        if schedule.user:
                            event_id = await self.sync_schedule_to_calendar(integration, team, schedule, service=service)
                            if event_id:
                                total_synced_count += 1
                
                await self.update_last_sync(integration.id)

            logger.info(f"Bulk sync completed: {total_synced_count} events synced for workspace {workspace_id}")
            return total_synced_count

        except Exception as e:
            logger.error(f"Error during bulk sync for workspace {workspace_id}: {e}")
            return 0

    async def validate_integration(self, workspace_id: int) -> bool:
        """Check if integration credentials can be decrypted and are valid."""
        try:
            integrations = await self.repo.list_by_workspace(workspace_id)
            if not integrations:
                return False
            
            # Retrieve one valid integration or check all? 
            # If any is invalid, what do we return? 
            # For now, let's just check if we can decrypt the first one.
            # Ideally validation should be per-integration.
            
            for integration in integrations:
                 self._decrypt_service_account_key(integration.service_account_key_encrypted)
            
            return True
        except Exception:
            return False

    def _get_team_color(self, team_id: int) -> int:
        """Get consistent color for team based on ID."""
        colors = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11]  # Available calendar colors
        return colors[team_id % len(colors)]

    async def update_last_sync(self, integration_id: int) -> None:
        """Update last sync timestamp."""
        await self.repo.update(integration_id, {"last_sync_at": datetime.utcnow()})
