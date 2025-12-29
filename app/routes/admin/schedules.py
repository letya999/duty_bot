"""Schedule management routes for web admin panel"""
import logging
from datetime import datetime, timedelta
from fastapi import APIRouter, Request, HTTPException, Depends
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy import select
from sqlalchemy.orm import joinedload, selectinload

from app.database import AsyncSessionLocal
from app.models import Schedule, User, Team, Workspace
from app.auth import session_manager
from app.services.schedule_service import ScheduleService

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/web/schedules", tags=["schedules"])


async def get_session_from_cookie(request: Request):
    """Extract and validate session from cookies"""
    token = request.cookies.get('session_token')
    if not token:
        raise HTTPException(status_code=401, detail="Not authenticated")

    session = await session_manager.validate_session(token)
    if not session:
        raise HTTPException(status_code=401, detail="Invalid or expired session")

    return session


@router.get("")
async def schedules_page(request: Request, session: dict = Depends(get_session_from_cookie)):
    """Schedule management page - Redirect to modern React dashboard"""
    return RedirectResponse(url="/schedules")


def generate_calendar(year, month, schedules):
    """Generate calendar HTML table"""
    import calendar

    # Get calendar matrix
    cal = calendar.monthcalendar(year, month)

    # Create schedule map
    schedule_map = {}
    for schedule in schedules:
        key = schedule.date.strftime("%Y-%m-%d")
        # Maybe I should check if `schedule.duty_date` is correct.
        # I'll change it to `schedule.date` because I know the model has it.
        # Wait, the original code had:
        # key = schedule.duty_date.strftime("%Y-%m-%d")
        # If I change it to `schedule.date`, I might fix a bug or break something if `duty_date` was a property.
        # Looking at models.py, `Schedule` class has `date` column. No `duty_date`.
        # So maybe the original code WAS BROKEN there too? Or maybe `schedule` passed to it was not a raw model?
        # In schedules_page, `schedules = result.unique().scalars().all()`. These are raw models.
        # So `schedule.duty_date` would fail unless added dynamically.
        # I will change it to `schedule.date` to be safe and correct.
        
        # ACTUALLY, checking the original code again (Step 35):
        # 370:         key = schedule.duty_date.strftime("%Y-%m-%d")
        
        # This looks wrong given `models.py`. 
        # But I'll fix it to `schedule.date` which I know is correct from `models.py`.
        
        key = schedule.date.strftime("%Y-%m-%d")
        
        if key not in schedule_map:
            schedule_map[key] = []
        schedule_map[key].append(schedule)

    # Generate table
    html = '<table><tr>'
    for day_name in ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']:
        html += f'<th>{day_name}</th>'
    html += '</tr>'

    for week in cal:
        html += '<tr>'
        for day in week:
            if day == 0:
                html += '<td class="other-month"></td>'
            else:
                date_str = f"{year}-{month:02d}-{day:02d}"
                duties_html = ''
                if date_str in schedule_map:
                    for schedule in schedule_map[date_str]:
                        duties_html += f'<div class="duty" onclick="editDuty({schedule.id})">'
                        duties_html += schedule.user.first_name or schedule.user.username
                        duties_html += '</div>'

                html += f'''<td>
                    <div class="date-num">{day}</div>
                    {duties_html}
                </td>'''
        html += '</tr>'

    html += '</table>'
    return html


def get_month_name(month):
    """Get month name"""
    months = ['January', 'February', 'March', 'April', 'May', 'June',
              'July', 'August', 'September', 'October', 'November', 'December']
    return months[month - 1]
