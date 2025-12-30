
import sys
import os
import asyncio
import logging

# Add current dir to path
sys.path.append(os.getcwd())

# Configure logging to stdout
logging.basicConfig(level=logging.INFO)

from app.database import AsyncSessionLocal
from app.repositories.google_calendar_repository import GoogleCalendarRepository
from app.repositories.schedule_repository import ScheduleRepository
from app.repositories.team_repository import TeamRepository
from app.services.google_calendar_service import GoogleCalendarService

async def main():
    async with AsyncSessionLocal() as session:
        print("Starting manual sync for workspace 2...")
        
        calendar_repo = GoogleCalendarRepository(session)
        schedule_repo = ScheduleRepository(session)
        team_repo = TeamRepository(session)
        
        service = GoogleCalendarService(calendar_repo)
        
        # Sync workspace 2
        count = await service.sync_workspace_schedules(2, schedule_repo, team_repo)
        
        print(f"Manual sync finished. Synced {count} events.")

if __name__ == "__main__":
    if sys.platform == 'win32':
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(main())
