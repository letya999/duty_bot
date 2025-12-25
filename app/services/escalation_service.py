from app.models import Escalation, EscalationEvent, Team, User
from app.repositories import EscalationRepository, EscalationEventRepository


class EscalationService:
    def __init__(self, escalation_repo: EscalationRepository, escalation_event_repo: EscalationEventRepository = None):
        self.escalation_repo = escalation_repo
        self.escalation_event_repo = escalation_event_repo

    async def set_cto(self, workspace_id: int, user: User) -> Escalation:
        """Set CTO (level 2) for workspace"""
        return await self.escalation_repo.set_global_cto(user.id)

    async def get_cto(self, workspace_id: int) -> User | None:
        """Get CTO for workspace

        Note: Since CTOs are not directly workspace-scoped in the model,
        we get the user's workspace to ensure we return the correct context.
        """
        escalation = await self.escalation_repo.get_global_cto()

        if escalation and escalation.cto_user and escalation.cto_user.workspace_id == workspace_id:
            return escalation.cto_user
        return None

    async def create_escalation_event(
        self,
        team: Team,
        messenger: str
    ) -> EscalationEvent:
        """Create new escalation event"""
        if not self.escalation_event_repo:
            from app.database import AsyncSessionLocal
            async with AsyncSessionLocal() as session:
                self.escalation_event_repo = EscalationEventRepository(session)
                return await self.escalation_event_repo.create({
                    'team_id': team.id,
                    'messenger': messenger,
                })

        return await self.escalation_event_repo.create({
            'team_id': team.id,
            'messenger': messenger,
        })

    async def get_active_escalation(self, team: Team) -> EscalationEvent | None:
        """Get active escalation event (not acknowledged)"""
        if not self.escalation_event_repo:
            return None

        return await self.escalation_event_repo.get_active_escalation(team.id)

    async def acknowledge_escalation(self, event: EscalationEvent) -> EscalationEvent:
        """Acknowledge escalation event"""
        if not self.escalation_event_repo:
            return event

        return await self.escalation_event_repo.acknowledge_escalation(event.id)

    async def escalate_to_level2(self, event: EscalationEvent) -> EscalationEvent:
        """Mark escalation as escalated to level 2"""
        if not self.escalation_event_repo:
            return event

        return await self.escalation_event_repo.escalate_to_level2(event.id)
