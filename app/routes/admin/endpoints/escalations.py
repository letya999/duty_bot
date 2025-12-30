"""Escalation management endpoints"""
import logging
from fastapi import APIRouter, Depends, HTTPException, Body
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import get_db, get_current_user
from app.models import User, Escalation
from app.routes.admin.dependencies import get_escalation_service, get_admin_service

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/escalations", tags=["Escalations"])


@router.get(
    "",
    summary="List escalations",
    description="Get a list of escalations (CTO assignments) for all teams or a specific team."
)
async def get_escalations(
    team_id: int | None = None,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> list:
    """Get escalations"""
    try:
        if team_id:
            stmt = select(Escalation).where(Escalation.team_id == team_id)
        else:
            stmt = select(Escalation)

        stmt = stmt.options(selectinload(Escalation.team), selectinload(Escalation.cto_user))
        result = await db.execute(stmt)
        escalations = result.scalars().all()

        return [
            {
                "id": e.id,
                "team_id": e.team_id,
                "cto_id": e.cto_id,
                "team": {"id": e.team.id, "name": e.team.name} if e.team else None,
                "cto_user": {
                    "id": e.cto_user.id,
                    "first_name": e.cto_user.first_name,
                    "last_name": e.cto_user.last_name
                } if e.cto_user else None
            }
            for e in escalations
        ]
    except Exception as e:
        logger.error(f"Error getting escalations: {e}")
        raise HTTPException(status_code=500, detail="Failed to get escalations")


@router.post(
    "",
    summary="Create escalation",
    description="Create a new escalation (assign CTO to a team or set global CTO)."
)
async def create_escalation(
    team_id: int | None = Body(None, embed=False),
    cto_id: int = Body(..., embed=False),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    admin_service = Depends(get_admin_service)
) -> dict:
    """Create escalation"""
    try:
        if not user.is_admin:
            raise HTTPException(status_code=403, detail="Only admins can manage escalations")

        escalation = Escalation(
            team_id=team_id,
            cto_id=cto_id
        )
        db.add(escalation)
        await db.commit()

        # Log the action
        await admin_service.log_action(
            workspace_id=user.workspace_id,
            admin_id=user.id,
            action="create_escalation",
            target_user_id=cto_id,
            details={"escalation_id": escalation.id, "team_id": team_id},
            target_id=escalation.id,
            resource_type="escalation"
        )

        return {
            "id": escalation.id,
            "team_id": escalation.team_id,
            "cto_id": escalation.cto_id
        }
    except Exception as e:
        logger.error(f"Error creating escalation: {e}")
        raise HTTPException(status_code=500, detail="Failed to create escalation")


@router.delete(
    "/{escalation_id}",
    summary="Delete escalation",
    description="Delete an escalation (revoke CTO assignment)."
)
async def delete_escalation(
    escalation_id: int,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    admin_service = Depends(get_admin_service)
) -> dict:
    """Delete escalation"""
    try:
        if not user.is_admin:
            raise HTTPException(status_code=403, detail="Only admins can manage escalations")

        stmt = select(Escalation).where(Escalation.id == escalation_id)
        result = await db.execute(stmt)
        escalation = result.scalar_one_or_none()

        if not escalation:
            raise HTTPException(status_code=404, detail="Escalation not found")

        await db.delete(escalation)
        await db.commit()

        # Log the action
        await admin_service.log_action(
            workspace_id=user.workspace_id,
            admin_id=user.id,
            action="delete_escalation",
            target_user_id=escalation.cto_id if escalation else None,
            details={"escalation_id": escalation_id, "team_id": escalation.team_id if escalation else None},
            target_id=escalation_id,
            resource_type="escalation"
        )

        return {"status": "deleted"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting escalation: {e}")
        raise HTTPException(status_code=500, detail="Failed to delete escalation")
