"""Service for Google Calendar integration."""

import logging
import json
from datetime import datetime, date as date_type, timedelta
from typing import Optional, Dict, Any
from google.oauth2.service_account import Credentials
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from app.models import GoogleCalendarIntegration, Schedule, Shift, Team, User
from app.repositories.google_calendar_repository import GoogleCalendarRepository
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
            return build('calendar', 'v3', credentials=credentials)
        except Exception as e:
            logger.error(f"Failed to create Google Calendar service: {e}")
            raise ValidationError("Failed to authenticate with Google Calendar")

    async def setup_google_calendar(
        self,
        workspace_id: int,
        service_account_key: Dict[str, Any]
    ) -> GoogleCalendarIntegration:
        """Setup Google Calendar integration for workspace."""
        try:
            # Validate service account key
            if 'client_email' not in service_account_key:
                raise ValidationError("Invalid service account key format")

            service = self._get_calendar_service(service_account_key)

            # Create a new calendar
            calendar_body = {
                'summary': f'Duty Schedule',
                'description': 'Team duty rotation schedule',
                'timeZone': 'UTC'
            }

            calendar = service.calendars().insert(body=calendar_body).execute()
            calendar_id = calendar['id']

            # Make calendar public
            rule = {
                'scope': {'type': 'default'},
                'role': 'reader'
            }
            service.acl().insert(calendarId=calendar_id, body=rule).execute()

            # Get public calendar URL
            public_url = f"https://calendar.google.com/calendar/u/0?cid={calendar_id}"

            # Encrypt service account key
            encrypted_key = encrypt_string(json.dumps(service_account_key))

            # Create integration record
            integration = GoogleCalendarIntegration(
                workspace_id=workspace_id,
                service_account_key_encrypted=encrypted_key,
                google_calendar_id=calendar_id,
                public_calendar_url=public_url,
                service_account_email=service_account_key['client_email'],
                is_active=True
            )

            await self.repo.create(integration)
            logger.info(f"Google Calendar setup complete for workspace {workspace_id}")

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
        schedule: Schedule
    ) -> Optional[str]:
        """Sync duty schedule to Google Calendar. Returns event ID."""
        try:
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

            # Create event
            event = service.events().insert(
                calendarId=integration.google_calendar_id,
                body=event_body
            ).execute()

            event_id = event['id']
            logger.info(f"Created calendar event {event_id} for schedule {schedule.id}")

            return event_id

        except HttpError as e:
            logger.error(f"Google API error while syncing schedule: {e}")
        except Exception as e:
            logger.error(f"Error syncing schedule to calendar: {e}")

        return None

    async def sync_shift_to_calendar(
        self,
        integration: GoogleCalendarIntegration,
        team: Team,
        shift: Shift
    ) -> Optional[str]:
        """Sync shift to Google Calendar. Returns event ID."""
        try:
            service_account_key = self._decrypt_service_account_key(
                integration.service_account_key_encrypted
            )
            service = self._get_calendar_service(service_account_key)

            # Get user names
            user_names = ', '.join([u.first_name or u.username for u in shift.users])

            # Create event body
            end_date = shift.date + timedelta(days=1)
            event_body = {
                'summary': f"👥 {team.display_name} - {user_names}",
                'description': f"Shift for {team.display_name}: {user_names}",
                'start': {
                    'date': shift.date.isoformat()
                },
                'end': {
                    'date': end_date.isoformat()
                },
                'colorId': str(self._get_team_color(team.id))
            }

            # Create event
            event = service.events().insert(
                calendarId=integration.google_calendar_id,
                body=event_body
            ).execute()

            event_id = event['id']
            logger.info(f"Created calendar event {event_id} for shift {shift.id}")

            return event_id

        except HttpError as e:
            logger.error(f"Google API error while syncing shift: {e}")
        except Exception as e:
            logger.error(f"Error syncing shift to calendar: {e}")

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

            service.events().delete(
                calendarId=integration.google_calendar_id,
                eventId=event_id
            ).execute()

            logger.info(f"Deleted calendar event {event_id}")
            return True

        except HttpError as e:
            logger.error(f"Google API error while deleting event: {e}")
        except Exception as e:
            logger.error(f"Error deleting calendar event: {e}")

        return False

    async def disconnect_google_calendar(self, workspace_id: int) -> bool:
        """Disconnect Google Calendar from workspace."""
        try:
            integration = await self.repo.get_by_workspace(workspace_id)
            if not integration:
                return False

            service_account_key = self._decrypt_service_account_key(
                integration.service_account_key_encrypted
            )
            service = self._get_calendar_service(service_account_key)

            # Delete the calendar
            try:
                service.calendars().delete(
                    calendarId=integration.google_calendar_id
                ).execute()
            except HttpError as e:
                logger.warning(f"Could not delete calendar from Google: {e}")

            # Delete integration record
            await self.repo.delete(integration.id)
            logger.info(f"Google Calendar disconnected for workspace {workspace_id}")

            return True

        except Exception as e:
            logger.error(f"Error disconnecting Google Calendar: {e}")
            return False

    def _get_team_color(self, team_id: int) -> int:
        """Get consistent color for team based on ID."""
        colors = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11]  # Available calendar colors
        return colors[team_id % len(colors)]

    async def update_last_sync(self, workspace_id: int) -> None:
        """Update last sync timestamp."""
        integration = await self.repo.get_by_workspace(workspace_id)
        if integration:
            integration.last_sync_at = datetime.utcnow()
            await self.repo.update(integration)
