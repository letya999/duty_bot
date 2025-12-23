from datetime import datetime, timezone
from zoneinfo import ZoneInfo
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from app.models import Escalation, EscalationEvent, Team, User
from app.config import get_settings


class EscalationService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def set_cto(self, workspace_id: int, user: User) -> Escalation:
        """Set CTO (level 2) for workspace"""
        stmt = select(Escalation).where(
            (Escalation.team_id.is_(None)) &
            (Escalation.cto_id == user.id)
        )
        # Try to get existing escalation with this CTO
        result = await self.db.execute(stmt)
        escalation = result.scalars().first()

        if not escalation:
            # Create new escalation record
            escalation = Escalation(cto_id=user.id)
            self.db.add(escalation)
            await self.db.commit()
            await self.db.refresh(escalation)

        return escalation

    async def get_cto(self, workspace_id: int) -> User | None:
        """Get CTO for workspace

        Note: Since CTOs are not directly workspace-scoped in the model,
        we get the user's workspace to ensure we return the correct context.
        """
        stmt = select(Escalation).options(
            selectinload(Escalation.cto_user)
        ).where(Escalation.team_id.is_(None))
        result = await self.db.execute(stmt)
        escalation = result.scalars().first()

        if escalation and escalation.cto_user and escalation.cto_user.workspace_id == workspace_id:
            return escalation.cto_user
        return None

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
        settings = get_settings()
        tz = ZoneInfo(settings.timezone)
        event.acknowledged_at = datetime.now(tz)
        await self.db.commit()
        await self.db.refresh(event)
        return event

    async def escalate_to_level2(self, event: EscalationEvent) -> EscalationEvent:
        """Mark escalation as escalated to level 2"""
        settings = get_settings()
        tz = ZoneInfo(settings.timezone)
        event.escalated_to_level2_at = datetime.now(tz)
        await self.db.commit()
        await self.db.refresh(event)
        return event
