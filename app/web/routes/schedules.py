"""Schedule management routes for web admin panel"""
import logging
from datetime import datetime, timedelta
from fastapi import APIRouter, Request, HTTPException, Depends
from fastapi.responses import HTMLResponse
from sqlalchemy import select
from sqlalchemy.orm import joinedload

from app.database import AsyncSessionLocal
from app.models import Schedule, Shift, User, Team, Workspace
from app.web.auth import session_manager
from app.services.schedule_service import ScheduleService

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/web/schedules", tags=["schedules"])


def get_session_from_cookie(request: Request):
    """Extract and validate session from cookies"""
    token = request.cookies.get('session_token')
    if not token:
        raise HTTPException(status_code=401, detail="Not authenticated")

    session = session_manager.validate_session(token)
    if not session:
        raise HTTPException(status_code=401, detail="Invalid or expired session")

    return session


@router.get("")
async def schedules_page(request: Request, session: dict = Depends(get_session_from_cookie)):
    """Schedule management page with calendar view"""
    try:
        async with AsyncSessionLocal() as db:
            workspace_id = session['workspace_id']
            year = int(request.query_params.get('year', datetime.now().year))
            month = int(request.query_params.get('month', datetime.now().month))

            # Get all teams for filter
            stmt = select(Team).where(Team.workspace_id == workspace_id)
            result = await db.execute(stmt)
            teams = result.scalars().all()

            # Get all users for assignment
            stmt = select(User).where(User.workspace_id == workspace_id)
            result = await db.execute(stmt)
            users = result.scalars().all()

            # Get schedules for current month
            start_date = datetime(year, month, 1).date()
            if month == 12:
                end_date = datetime(year + 1, 1, 1).date() - timedelta(days=1)
            else:
                end_date = datetime(year, month + 1, 1).date() - timedelta(days=1)

            stmt = select(Schedule).where(
                (Schedule.workspace_id == workspace_id) &
                (Schedule.duty_date >= start_date) &
                (Schedule.duty_date <= end_date)
            ).options(joinedload(Schedule.user), joinedload(Schedule.team))
            result = await db.execute(stmt)
            schedules = result.unique().scalars().all()

            # Build calendar
            calendar_html = generate_calendar(year, month, schedules)

            # Build team options
            team_options = ''.join(f'<option value="{team.id}">{team.name}</option>' for team in teams)
            user_options = ''.join(f'<option value="{user.id}">{user.first_name or user.username}</option>' for user in users)

            html = f"""
            <!DOCTYPE html>
            <html>
            <head>
                <title>Schedule Management - Duty Bot</title>
                <meta charset="utf-8">
                <meta name="viewport" content="width=device-width, initial-scale=1">
                <style>
                    * {{ margin: 0; padding: 0; box-sizing: border-box; }}
                    body {{
                        font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                        background: #f5f5f5;
                    }}
                    .header {{
                        background: white;
                        border-bottom: 1px solid #e0e0e0;
                        padding: 20px;
                        display: flex;
                        justify-content: space-between;
                        align-items: center;
                    }}
                    nav {{
                        background: white;
                        padding: 15px 20px;
                        border-bottom: 1px solid #e0e0e0;
                        margin-bottom: 20px;
                    }}
                    nav a {{
                        display: inline-block;
                        margin-right: 20px;
                        text-decoration: none;
                        color: #666;
                        font-weight: 500;
                    }}
                    nav a.active {{ color: #667eea; border-bottom: 2px solid #667eea; padding-bottom: 5px; }}
                    .container {{
                        max-width: 1400px;
                        margin: 20px auto;
                        padding: 0 20px;
                    }}
                    .controls {{
                        background: white;
                        padding: 20px;
                        border-radius: 8px;
                        margin-bottom: 20px;
                        box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
                        display: flex;
                        gap: 15px;
                        flex-wrap: wrap;
                    }}
                    .controls input, .controls select {{
                        padding: 10px;
                        border: 1px solid #ddd;
                        border-radius: 5px;
                        font-size: 14px;
                    }}
                    .controls button {{
                        padding: 10px 20px;
                        background: #667eea;
                        color: white;
                        border: none;
                        border-radius: 5px;
                        cursor: pointer;
                    }}
                    .controls button:hover {{ background: #5568d3; }}
                    .calendar {{
                        background: white;
                        padding: 20px;
                        border-radius: 8px;
                        box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
                    }}
                    .calendar-header {{
                        text-align: center;
                        margin-bottom: 20px;
                        font-size: 18px;
                        font-weight: bold;
                    }}
                    .calendar-nav {{
                        display: flex;
                        justify-content: space-between;
                        margin-bottom: 20px;
                    }}
                    .calendar-nav a {{
                        padding: 10px 15px;
                        background: #f0f0f0;
                        border-radius: 5px;
                        text-decoration: none;
                        color: #333;
                    }}
                    .calendar-nav a:hover {{ background: #e0e0e0; }}
                    table {{
                        width: 100%;
                        border-collapse: collapse;
                    }}
                    th {{
                        background: #f9f9f9;
                        padding: 12px;
                        text-align: center;
                        border-bottom: 2px solid #e0e0e0;
                    }}
                    td {{
                        width: 14.28%;
                        height: 100px;
                        padding: 10px;
                        border: 1px solid #e0e0e0;
                        vertical-align: top;
                        background: white;
                    }}
                    td.other-month {{ background: #f9f9f9; }}
                    .date-num {{
                        font-weight: bold;
                        margin-bottom: 5px;
                    }}
                    .duty {{
                        background: #e8f4f8;
                        padding: 4px 8px;
                        border-radius: 3px;
                        font-size: 12px;
                        margin-bottom: 4px;
                        cursor: pointer;
                    }}
                    .duty:hover {{ background: #d0e8f0; }}
                    .modal {{
                        display: none;
                        position: fixed;
                        top: 0;
                        left: 0;
                        width: 100%;
                        height: 100%;
                        background: rgba(0, 0, 0, 0.5);
                        z-index: 1000;
                        align-items: center;
                        justify-content: center;
                    }}
                    .modal.active {{ display: flex; }}
                    .modal-content {{
                        background: white;
                        padding: 30px;
                        border-radius: 10px;
                        width: 400px;
                    }}
                    .modal-content h2 {{ margin-bottom: 20px; }}
                    .modal-content label {{
                        display: block;
                        margin-bottom: 5px;
                        font-weight: 500;
                    }}
                    .modal-content select, .modal-content input {{
                        width: 100%;
                        padding: 10px;
                        margin-bottom: 15px;
                        border: 1px solid #ddd;
                        border-radius: 5px;
                    }}
                    .modal-buttons {{
                        display: flex;
                        gap: 10px;
                        justify-content: flex-end;
                    }}
                    .modal-buttons button {{
                        padding: 10px 20px;
                        border: none;
                        border-radius: 5px;
                        cursor: pointer;
                    }}
                    .btn-primary {{
                        background: #667eea;
                        color: white;
                    }}
                    .btn-secondary {{
                        background: #e0e0e0;
                        color: #333;
                    }}
                    .logout-btn {{
                        background: #e74c3c;
                        color: white;
                        border: none;
                        padding: 10px 20px;
                        border-radius: 5px;
                        cursor: pointer;
                        text-decoration: none;
                    }}
                </style>
            </head>
            <body>
                <div class="header">
                    <h1>📅 Schedule Management</h1>
                    <a href="/web/auth/logout" class="logout-btn">Logout</a>
                </div>

                <nav>
                    <a href="/web/dashboard">Dashboard</a>
                    <a href="/web/schedules" class="active">Schedules</a>
                    <a href="/web/settings">Settings</a>
                    <a href="/web/reports">Reports</a>
                </nav>

                <div class="container">
                    <div class="controls">
                        <select id="teamFilter">
                            <option value="">All Teams</option>
                            {team_options}
                        </select>
                        <button onclick="addDuty()">➕ Add Duty</button>
                        <button onclick="bulkAssign()">📋 Bulk Assign</button>
                    </div>

                    <div class="calendar">
                        <div class="calendar-header">{get_month_name(month)} {year}</div>
                        <div class="calendar-nav">
                            <a href="?year={year if month > 1 else year - 1}&month={month - 1 if month > 1 else 12}">← Previous</a>
                            <a href="?year={datetime.now().year}&month={datetime.now().month}">Today</a>
                            <a href="?year={year if month < 12 else year + 1}&month={month + 1 if month < 12 else 1}">Next →</a>
                        </div>
                        {calendar_html}
                    </div>
                </div>

                <div id="modal" class="modal">
                    <div class="modal-content">
                        <h2>Add Duty Assignment</h2>
                        <label>Date</label>
                        <input type="date" id="dutyDate">
                        <label>User</label>
                        <select id="dutyUser">
                            {user_options}
                        </select>
                        <label>Team (Optional)</label>
                        <select id="dutyTeam">
                            <option value="">No Team</option>
                            {team_options}
                        </select>
                        <div class="modal-buttons">
                            <button class="btn-secondary" onclick="closeModal()">Cancel</button>
                            <button class="btn-primary" onclick="saveDuty()">Save</button>
                        </div>
                    </div>
                </div>

                <script>
                    function addDuty() {{
                        document.getElementById('modal').classList.add('active');
                    }}

                    function closeModal() {{
                        document.getElementById('modal').classList.remove('active');
                    }}

                    function saveDuty() {{
                        const date = document.getElementById('dutyDate').value;
                        const userId = document.getElementById('dutyUser').value;
                        const teamId = document.getElementById('dutyTeam').value || null;

                        fetch('/api/miniapp/schedule/assign', {{
                            method: 'POST',
                            headers: {{'Content-Type': 'application/json'}},
                            body: JSON.stringify({{
                                duty_date: date,
                                user_id: parseInt(userId),
                                team_id: teamId ? parseInt(teamId) : null
                            }})
                        }}).then(r => r.json()).then(data => {{
                            if (data.success) {{
                                alert('Duty assigned successfully!');
                                closeModal();
                                location.reload();
                            }} else {{
                                alert('Error: ' + data.detail);
                            }}
                        }});
                    }}

                    function bulkAssign() {{
                        alert('Bulk assign feature coming soon!');
                    }}
                </script>
            </body>
            </html>
            """

            return HTMLResponse(content=html)

    except Exception as e:
        logger.error(f"Error rendering schedules page: {e}")
        raise HTTPException(status_code=500, detail=str(e))


def generate_calendar(year, month, schedules):
    """Generate calendar HTML table"""
    import calendar

    # Get calendar matrix
    cal = calendar.monthcalendar(year, month)

    # Create schedule map
    schedule_map = {}
    for schedule in schedules:
        key = schedule.duty_date.strftime("%Y-%m-%d")
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
