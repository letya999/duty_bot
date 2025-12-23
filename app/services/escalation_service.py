from datetime import datetime, timezone
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from app.models import Escalation, EscalationEvent, Team, User


class EscalationService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def set_cto(self, user: User) -> Escalation:
        """Set global CTO (level 2)"""
        stmt = select(Escalation).where(Escalation.team_id.is_(None))
        result = await self.db.execute(stmt)
        escalation = result.scalars().first()

        if escalation:
            escalation.cto_id = user.id
        else:
            escalation = Escalation(cto_id=user.id)
            self.db.add(escalation)

        await self.db.commit()
        await self.db.refresh(escalation)
        return escalation

    async def get_cto(self) -> User | None:
        """Get CTO"""
        stmt = select(Escalation).options(
            selectinload(Escalation.cto_user)
        ).where(Escalation.team_id.is_(None))
        result = await self.db.execute(stmt)
        escalation = result.scalars().first()
        return escalation.cto_user if escalation else None

    async def create_escalation_event(
        self,
        team: Team,
        messenger: str
    ) -> EscalationEvent:
        """Create new escalation event"""
        event = EscalationEvent(
            team_id=team.id,
            messenger=messenger,
        )
        self.db.add(event)
        await self.db.commit()
        await self.db.refresh(event)
        return event

    async def get_active_escalation(self, team: Team) -> EscalationEvent | None:
        """Get active escalation event (not acknowledged)"""
        stmt = select(EscalationEvent).where(
            (EscalationEvent.team_id == team.id) &
            (EscalationEvent.acknowledged_at.is_(None))
        ).order_by(EscalationEvent.initiated_at.desc())
        result = await self.db.execute(stmt)
        return result.scalars().first()

    async def acknowledge_escalation(self, event: EscalationEvent) -> EscalationEvent:
        """Acknowledge escalation event"""
        event.acknowledged_at = datetime.now(timezone.utc)
        await self.db.commit()
        await self.db.refresh(event)
        return event

    async def escalate_to_level2(self, event: EscalationEvent) -> EscalationEvent:
        """Mark escalation as escalated to level 2"""
        event.escalated_to_level2_at = datetime.now(timezone.utc)
        await self.db.commit()
        await self.db.refresh(event)
        return event
