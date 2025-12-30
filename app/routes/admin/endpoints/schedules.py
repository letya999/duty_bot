"""Schedule and shift management endpoints"""
import logging
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException, Body
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import get_db, get_current_user
from app.models import User, Schedule
from app.services.schedule_service import ScheduleService
from app.services.team_service import TeamService
from app.repositories import ScheduleRepository, TeamRepository
from app.exceptions import NotFoundError, AuthorizationError, ValidationError
from app.routes.admin.dependencies import get_schedule_service, get_team_service, get_admin_service

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/schedule", tags=["Schedules"])


@router.get(
    "/month",
    summary="Get month schedule",
    description="Get duty assignments for a month with specified year and month."
)
async def get_month_schedule(
    year: int,
    month: int,
    user: User = Depends(get_current_user),
    schedule_service: ScheduleService = Depends(get_schedule_service),
    team_service: TeamService = Depends(get_team_service),
    db: AsyncSession = Depends(get_db)
) -> dict:
    """Get schedule for a month"""
    try:
        from app.config.api_utils import (
            get_month_dates,
            get_schedules_for_period,
            build_schedule_by_date,
            build_days_array
        )

        start_date, end_date = await get_month_dates(year, month)
        schedules = await get_schedules_for_period(db, user, start_date, end_date)

        schedule_by_date = await build_schedule_by_date(schedules)
        days = await build_days_array(start_date, end_date, schedule_by_date)

        return {
            "year": year,
            "month": month,
            "days": days
        }
    except Exception as e:
        logger.error(f"Error getting month schedule: {e}")
        raise HTTPException(status_code=500, detail="Failed to get schedule")


@router.get(
    "/day/{date}",
    summary="Get daily schedule",
    description="Get duty assignments for a specific day."
)
async def get_daily_schedule(
    date: str,
    user: User = Depends(get_current_user),
    schedule_service: ScheduleService = Depends(get_schedule_service),
    team_service: TeamService = Depends(get_team_service),
    db: AsyncSession = Depends(get_db)
) -> dict:
    """Get schedule for a specific day"""
    try:
        from datetime import datetime as dt
        from app.config.api_utils import (
            get_daily_schedules,
            build_daily_users_list
        )

        date_obj = dt.fromisoformat(date).date()
        schedules = await get_daily_schedules(db, user, date_obj)
        users_result = await build_daily_users_list(schedules)

        return {
            "date": date,
            "users": users_result["users"],
            "count": users_result["count"]
        }
    except Exception as e:
        logger.error(f"Error getting daily schedule: {e}")
        raise HTTPException(status_code=500, detail="Failed to get schedule")


@router.post(
    "/assign",
    summary="Create or update duty assignment",
    description="Assign a user to duty on a specific day."
)
async def assign_duty(
    user_id: int = Body(..., embed=True),
    duty_date: str = Body(..., embed=True),
    team_id: int = Body(..., embed=True),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    admin_service = Depends(get_admin_service)
) -> dict:
    """Assign duty to a user"""
    try:
        from datetime import datetime as dt

        schedule_service = ScheduleService(ScheduleRepository(db))
        team_service = TeamService(TeamRepository(db))

        team = await team_service.get_team(team_id, current_user.workspace_id)
        if not team:
            raise HTTPException(status_code=404, detail="Team not found")

        target_user = await db.get(User, user_id)
        if not target_user:
            raise HTTPException(status_code=404, detail="User not found")

        # Allow if same workspace, same organization, or if current user is superadmin
        is_same_workspace = target_user.workspace_id == current_user.workspace_id
        is_same_org = (
            target_user.organization_id is not None and
            target_user.organization_id == current_user.organization_id
        )

        if not (is_same_workspace or is_same_org or current_user.is_superadmin):
            raise HTTPException(status_code=400, detail="User not found in workspace context")

        date_obj = dt.fromisoformat(duty_date).date()

        schedule = await schedule_service.set_duty(
            team.id,
            target_user.id,
            date_obj,
            is_shift=team.has_shifts
        )

        # Log the action
        await admin_service.log_action(
            workspace_id=current_user.workspace_id,
            admin_id=current_user.id,
            action="assign_duty",
            target_user_id=user_id,
            details={"team_id": team_id, "duty_date": duty_date, "is_shift": team.has_shifts},
            target_id=schedule.id,
            resource_type="schedule"
        )

        return {
            "status": "assigned",
            "schedule_id": schedule.id,
            "date": duty_date,
            "is_shift": schedule.is_shift
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error assigning duty: {e}")
        raise HTTPException(status_code=500, detail="Failed to assign duty")


@router.delete(
    "/{schedule_id}",
    summary="Delete duty assignment",
    description="Delete a duty assignment by its ID."
)
async def remove_duty(
    schedule_id: int,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    admin_service = Depends(get_admin_service)
) -> dict:
    """Remove duty assignment"""
    try:
        # Use select with selectinload to avoid lazy-loading error
        stmt = select(Schedule).where(Schedule.id == schedule_id).options(selectinload(Schedule.team))
        result = await db.execute(stmt)
        schedule_obj = result.scalar_one_or_none()

        if not schedule_obj:
            raise NotFoundError("Schedule")

        if schedule_obj.team.workspace_id != user.workspace_id:
            raise AuthorizationError("Not authorized to modify this schedule")

        schedule_service = ScheduleService(ScheduleRepository(db))
        success = await schedule_service.clear_duty(schedule_obj.team_id, schedule_obj.date)

        if not success:
            raise ValidationError("Failed to clear duty")

        # Log the action
        await admin_service.log_action(
            workspace_id=user.workspace_id,
            admin_id=user.id,
            action="remove_duty",
            target_user_id=schedule_obj.user_id,
            details={"team_id": schedule_obj.team_id, "duty_date": str(schedule_obj.date)},
            target_id=schedule_id,
            resource_type="schedule"
        )

        return {"status": "removed", "schedule_id": schedule_id}
    except (NotFoundError, AuthorizationError, ValidationError):
        raise
    except Exception as e:
        logger.error(f"Error removing duty: {e}")
        raise ValidationError("Failed to remove duty")


@router.put(
    "/{schedule_id}",
    summary="Update duty assignment",
    description="Update an existing duty assignment (user, date, or team)."
)
async def update_duty(
    schedule_id: int,
    user_id: int = Body(..., embed=False),
    duty_date: str = Body(..., embed=False),
    team_id: int | None = Body(None, embed=False),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    admin_service = Depends(get_admin_service)
) -> dict:
    """Update existing duty assignment"""
    try:
        if not user.is_admin:
            raise HTTPException(status_code=403, detail="Only admins can update duties")

        schedule_service = ScheduleService(ScheduleRepository(db))
        team_service = TeamService(TeamRepository(db))

        team = await team_service.get_team(team_id) if team_id else None
        duty_date_obj = datetime.fromisoformat(duty_date).date()
        schedule = await schedule_service.update_duty(schedule_id, user_id, duty_date_obj, team)

        # Log the action
        await admin_service.log_action(
            workspace_id=user.workspace_id,
            admin_id=user.id,
            action="update_duty",
            target_user_id=user_id,
            details={"team_id": team_id, "duty_date": duty_date},
            target_id=schedule_id,
            resource_type="schedule"
        )

        return {
            "id": schedule.id,
            "user_id": schedule.user_id,
            "duty_date": schedule.date.isoformat() if hasattr(schedule.date, 'isoformat') else str(schedule.date),
            "team_id": schedule.team_id,
        }
    except Exception as e:
        logger.error(f"Error updating duty: {e}")
        raise HTTPException(status_code=500, detail="Failed to update duty")


@router.post(
    "/assign-bulk",
    summary="Bulk assign duties",
    description="Assign multiple users to a date range in bulk."
)
async def assign_bulk_duties(
    user_ids: list[int] = Body(..., embed=False),
    start_date: str = Body(..., embed=False),
    end_date: str = Body(..., embed=False),
    team_id: int | None = Body(None, embed=False),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    admin_service = Depends(get_admin_service)
) -> dict:
    """Assign multiple users to dates in range"""
    try:
        logger.info(f"🔵 Bulk assign started: users={user_ids}, range={start_date} to {end_date}, team={team_id}")
        if not user.is_admin:
            logger.warning(f"❌ User {user.id} tried to bulk assign without admin perms")
            raise HTTPException(status_code=403, detail="Only admins can assign duties")

        schedule_service = ScheduleService(ScheduleRepository(db))
        team_service = TeamService(TeamRepository(db))

        start = datetime.strptime(start_date, '%Y-%m-%d').date()
        end = datetime.strptime(end_date, '%Y-%m-%d').date()

        team = await team_service.get_team(team_id, user.workspace_id) if team_id else None

        if not team:
            logger.error(f"❌ Team {team_id} not found or access denied")
            raise HTTPException(status_code=400, detail="Team is required for bulk assignment")

        created_count = 0
        current_date = start
        while current_date <= end:
            for user_id in user_ids:
                try:
                    logger.debug(f"📅 Setting duty for user {user_id} on {current_date} (is_shift={team.has_shifts})")
                    await schedule_service.set_duty(
                        team.id,
                        user_id,
                        current_date,
                        is_shift=team.has_shifts,
                        commit=False
                    )
                    created_count += 1
                except Exception as e:
                    logger.warning(f"❌ Failed to set duty for user {user_id} on {current_date}: {e}")
            current_date += timedelta(days=1)

        logger.info(f"💾 Committing {created_count} assignments to database")
        await db.commit()
        logger.info(f"✅ Bulk assign completed successfully")

        # Log the action
        await admin_service.log_action(
            workspace_id=user.workspace_id,
            admin_id=user.id,
            action="assign_bulk_duties",
            details={
                "team_id": team_id,
                "user_count": len(user_ids),
                "start_date": start_date,
                "end_date": end_date,
                "created_count": created_count
            },
            target_id=team_id,
            resource_type="team"
        )

        return {"created": created_count, "total_expected": len(user_ids) * ((end - start).days + 1)}
    except Exception as e:
        logger.error(f"Error assigning bulk duties: {e}")
        raise HTTPException(status_code=500, detail="Failed to assign bulk duties")


@router.patch(
    "/{schedule_id}/move",
    summary="Move duty to another date",
    description="Move a duty assignment to another date."
)
async def move_duty(
    schedule_id: int,
    new_date: str = Body(..., embed=True),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> dict:
    """Move duty to different date"""
    try:
        if not user.is_admin:
            raise HTTPException(status_code=403, detail="Only admins can modify duties")

        new_date_obj = datetime.strptime(new_date, '%Y-%m-%d').date()

        stmt = select(Schedule).where(Schedule.id == schedule_id)
        result = await db.execute(stmt)
        schedule = result.scalar_one_or_none()

        if not schedule:
            raise HTTPException(status_code=404, detail="Schedule not found")

        schedule.date = new_date_obj
        await db.commit()

        return {"status": "moved", "new_date": new_date}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error moving duty: {e}")
        raise HTTPException(status_code=500, detail="Failed to move duty")


@router.patch(
    "/{schedule_id}/replace",
    summary="Replace duty person",
    description="Replace a person on duty with another user."
)
async def replace_duty_user(
    schedule_id: int,
    user_id: int = Body(..., embed=True),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> dict:
    """Replace person in duty with different user"""
    try:
        if not user.is_admin:
            raise HTTPException(status_code=403, detail="Only admins can modify duties")

        stmt = select(Schedule).where(Schedule.id == schedule_id)
        result = await db.execute(stmt)
        schedule = result.scalar_one_or_none()

        if not schedule:
            raise HTTPException(status_code=404, detail="Schedule not found")

        schedule.user_id = user_id
        await db.commit()

        return {"status": "replaced", "user_id": user_id}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error replacing duty user: {e}")
        raise HTTPException(status_code=500, detail="Failed to replace duty user")


# Shift endpoints for teams with has_shifts=True
shifts_router = APIRouter(prefix="/shifts", tags=["Schedules"])


@shifts_router.post(
    "/assign",
    summary="Assign user to shift",
    description="Add a user to a shift. Used for teams with shifts enabled (has_shifts=true)."
)
async def assign_shift(
    user_id: int = Body(..., embed=True),
    shift_date: str = Body(..., embed=True),
    team_id: int = Body(..., embed=True),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> dict:
    """Assign user to shift - for teams with shifts enabled"""
    try:
        from datetime import datetime as dt

        schedule_service = ScheduleService(ScheduleRepository(db))
        team_service = TeamService(TeamRepository(db))

        team = await team_service.get_team(team_id, current_user.workspace_id)
        if not team:
            raise HTTPException(status_code=404, detail="Team not found")
        if not team.has_shifts:
            raise HTTPException(status_code=400, detail="This team does not have shifts enabled")

        target_user = await db.get(User, user_id)
        if not target_user:
            raise HTTPException(status_code=404, detail="User not found")
            
        # Allow if same workspace, same organization, or if current user is superadmin
        is_same_workspace = target_user.workspace_id == current_user.workspace_id
        is_same_org = (
            target_user.organization_id is not None and 
            target_user.organization_id == current_user.organization_id
        )
        
        if not (is_same_workspace or is_same_org or current_user.is_superadmin):
            raise HTTPException(status_code=400, detail="User not found in workspace context")

        date_obj = dt.fromisoformat(shift_date).date()

        conflict = await schedule_service.check_user_schedule_conflict(target_user.id, date_obj, current_user.workspace_id)
        if conflict:
            raise HTTPException(status_code=409, detail=f"User already assigned to {conflict['team_name']} on this date")

        shift = await schedule_service.set_duty(team.id, target_user.id, date_obj, is_shift=True)

        return {
            "status": "assigned",
            "shift_id": shift.id,
            "date": shift_date,
            "user_id": target_user.id
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error assigning shift: {e}")
        raise HTTPException(status_code=500, detail="Failed to assign shift")


@shifts_router.post(
    "/assign-bulk",
    summary="Bulk assign users to shifts",
    description="Add multiple users to shifts for a date range. Used for teams with shifts enabled."
)
async def assign_shifts_bulk(
    user_ids: list[int] = Body(..., embed=True),
    start_date: str = Body(..., embed=True),
    end_date: str = Body(..., embed=True),
    team_id: int = Body(..., embed=True),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> dict:
    """Bulk assign users to shifts for date range"""
    try:
        from datetime import datetime as dt

        schedule_service = ScheduleService(ScheduleRepository(db))
        team_service = TeamService(TeamRepository(db))

        team = await team_service.get_team(team_id, current_user.workspace_id)
        if not team:
            raise HTTPException(status_code=404, detail="Team not found")
        if not team.has_shifts:
            raise HTTPException(status_code=400, detail="This team does not have shifts enabled")

        start_date_obj = dt.fromisoformat(start_date).date()
        end_date_obj = dt.fromisoformat(end_date).date()

        current_date = start_date_obj
        assignments = []
        while current_date <= end_date_obj:
            for uid in user_ids:
                schedule = await schedule_service.set_duty(
                    team.id,
                    uid,
                    current_date,
                    is_shift=True,
                    commit=False
                )
                assignments.append({
                    "date": current_date.isoformat(),
                    "schedule_id": schedule.id,
                    "user_id": uid
                })
            current_date += timedelta(days=1)

        await db.commit()

        return {
            "status": "bulk_assigned",
            "total_assignments": len(assignments),
            "assignments": assignments
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error bulk assigning shifts: {e}")
        raise HTTPException(status_code=500, detail="Failed to bulk assign shifts")
