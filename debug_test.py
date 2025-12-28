import asyncio
import os
import sys

# Add project root to path
sys.path.append(os.path.abspath('.'))

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload, joinedload
from app.models import Base, User, Team, Workspace
import traceback

async def run_debug():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=True)
    AsyncSessionLocal = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        
    async with AsyncSessionLocal() as db:
        ws = Workspace(name="test", workspace_type="telegram", external_id="123")
        db.add(ws)
        await db.flush()
        
        user1 = User(workspace_id=ws.id, display_name="Lead User", telegram_username="user1", telegram_id=1)
        db.add(user1)
        await db.commit()
        
        team = Team(workspace_id=ws.id, name="backend", display_name="Backend Team", team_lead_id=user1.id)
        db.add(team)
        await db.commit()
        
        print("\n--- QUERYING TEAM ---\n")
        stmt = select(Team).where(Team.name == "backend").options(selectinload(Team.members), joinedload(Team.team_lead_user))
        res = await db.execute(stmt)
        team_obj = res.scalar_one()
        
        print("\n--- ACCESSING LEAD ---\n")
        try:
            print(f"Lead display_name: {team_obj.team_lead_user.display_name}")
        except Exception:
            traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(run_debug())
