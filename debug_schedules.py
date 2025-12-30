
import sys
import os
import asyncio
from datetime import date
from sqlalchemy import select
from sqlalchemy.orm import joinedload, selectinload

# Add current dir to path
sys.path.append(os.getcwd())

from app.database import AsyncSessionLocal
from app.models import Schedule, Team, GoogleCalendarIntegration, User

async def main():
    async with AsyncSessionLocal() as session:
        print("Checking schedules for 2025-12-30...")
        stmt = select(Schedule).options(
            joinedload(Schedule.user),
            joinedload(Schedule.team)
        ).where(Schedule.date == date(2025, 12, 30))
        
        result = await session.execute(stmt)
        schedules = result.scalars().all()
        
        print(f"Found {len(schedules)} schedules for 2025-12-30:")
        for s in schedules:
            user_name = s.user.first_name if s.user else "None"
            team_name = s.team.name if s.team else "None"
            ws_id = s.team.workspace_id if s.team else "None"
            print(f"- [ID: {s.id}] Team: {team_name} (ID: {s.team_id}), User: {user_name} (ID: {s.user_id}), Workspace: {ws_id}")

        print("\nChecking Google Calendar Integrations for Workspace 2...")
        stmt_int = select(GoogleCalendarIntegration).options(
            selectinload(GoogleCalendarIntegration.teams)
        ).where(GoogleCalendarIntegration.workspace_id == 2)
        result_int = await session.execute(stmt_int)
        integrations = result_int.scalars().all()
        
        print(f"Found {len(integrations)} integrations:")
        for i in integrations:
            linked_team_ids = [t.id for t in i.teams]
            print(f"- Integration ID: {i.id}, Active: {i.is_active}, Teams Linked IDs: {linked_team_ids}")
            
        print("\nChecking Teams in Workspace 2...")
        stmt_team = select(Team).where(Team.workspace_id == 2)
        result_team = await session.execute(stmt_team)
        teams = result_team.scalars().all()
        team_info = [(t.id, t.name) for t in teams]
        print(f"Found {len(teams)} teams in Workspace 2: {team_info}")

if __name__ == "__main__":
    if sys.platform == 'win32':
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(main())
