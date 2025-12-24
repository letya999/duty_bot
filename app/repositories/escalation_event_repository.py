"""Repository for EscalationEvent model."""

from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from app.models import EscalationEvent
from app.repositories.base_repository import BaseRepository


class EscalationEventRepository(BaseRepository[EscalationEvent]):
    """Repository for EscalationEvent operations."""

    def __init__(self, db: AsyncSession):
        super().__init__(db, EscalationEvent)

    async def get_active_escalation(self, team_id: int) -> Optional[EscalationEvent]:
        """Get active escalation event (not acknowledged) for team."""
        stmt = select(EscalationEvent).where(
            (EscalationEvent.team_id == team_id) &
            (EscalationEvent.acknowledged_at.is_(None))
        ).order_by(EscalationEvent.initiated_at.desc())
        result = await self.db.execute(stmt)
        return result.scalars().first()

    async def acknowledge_escalation(self, event_id: int) -> Optional[EscalationEvent]:
        """Mark escalation event as acknowledged."""
        from datetime import datetime
        from zoneinfo import ZoneInfo
        from app.config import get_settings

        settings = get_settings()
        tz = ZoneInfo(settings.timezone)

        return await self.update(event_id, {
            'acknowledged_at': datetime.now(tz)
        })

    async def escalate_to_level2(self, event_id: int) -> Optional[EscalationEvent]:
        """Mark escalation event as escalated to level 2."""
        from datetime import datetime
        from zoneinfo import ZoneInfo
        from app.config import get_settings

        settings = get_settings()
        tz = ZoneInfo(settings.timezone)

        return await self.update(event_id, {
            'escalated_to_level2_at': datetime.now(tz)
        })
