"""Report generation routes for web admin panel"""
import logging
import csv
import io
import json
from datetime import datetime, timedelta, date
from calendar import month_name
from fastapi import APIRouter, Request, HTTPException, Depends
from fastapi.responses import HTMLResponse, StreamingResponse
from sqlalchemy import select, func, and_
from sqlalchemy.orm import joinedload

from app.database import AsyncSessionLocal
from app.models import Schedule, User, Team, AdminLog, Workspace, Shift, DutyStats
from app.services.stats_service import StatsService
from app.web.auth import session_manager

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/web/reports", tags=["reports"])


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
async def reports_page(request: Request, session: dict = Depends(get_session_from_cookie)):
    """Reports and analytics page with Phase 5 statistics"""
    try:
        async with AsyncSessionLocal() as db:
            workspace_id = session['workspace_id']
            today = datetime.now().date()

            # Initialize stats service
            stats_service = StatsService(db)

            # Get current month statistics
            current_month_stats = await stats_service.get_workspace_monthly_stats(
                workspace_id, today.year, today.month
            )
            top_users = await stats_service.get_top_users_by_duties(
                workspace_id, today.year, today.month, 10
            )
            team_workload = await stats_service.get_team_workload(
                workspace_id, today.year, today.month
            )

            # Calculate summary stats
            total_duty_days = sum(s.duty_days for s in current_month_stats)
            total_shift_days = sum(s.shift_days for s in current_month_stats)
            total_records = len(current_month_stats)

            # Build user stats HTML
            user_stats_html = ''
            for rank, user in enumerate(top_users, 1):
                user_stats_html += f'''<tr>
                    <td>{rank}</td>
                    <td>{user['display_name']}</td>
                    <td>{user['total_duties']}</td>
                </tr>'''
            if not user_stats_html:
                user_stats_html = '<tr><td colspan="3">No data available</td></tr>'

            # Build team workload HTML
            team_stats_html = ''
            for team in team_workload:
                avg_duties = (
                    team['total_duties'] / team['team_members']
                    if team['team_members'] > 0
                    else 0
                )
                team_stats_html += f'''<tr>
                    <td>{team['team_name']}</td>
                    <td>{team['total_duties']}</td>
                    <td>{team['team_members']}</td>
                    <td>{avg_duties:.1f}</td>
                </tr>'''
            if not team_stats_html:
                team_stats_html = '<tr><td colspan="4">No data available</td></tr>'

            html = f"""
            <!DOCTYPE html>
            <html>
            <head>
                <title>Reports - Duty Bot</title>
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
                        max-width: 1200px;
                        margin: 20px auto;
                        padding: 0 20px;
                    }}
                    .stats {{
                        display: grid;
                        grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
                        gap: 20px;
                        margin-bottom: 30px;
                    }}
                    .stat-card {{
                        background: white;
                        padding: 20px;
                        border-radius: 8px;
                        box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
                    }}
                    .stat-card h3 {{ color: #666; font-size: 14px; margin-bottom: 10px; }}
                    .stat-card .value {{ font-size: 32px; font-weight: bold; color: #333; }}
                    .section {{
                        background: white;
                        padding: 20px;
                        border-radius: 8px;
                        box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
                        margin-bottom: 20px;
                    }}
                    .section h2 {{ margin-bottom: 15px; color: #333; }}
                    .report-controls {{
                        display: flex;
                        gap: 10px;
                        margin-bottom: 15px;
                        flex-wrap: wrap;
                    }}
                    .report-controls input, .report-controls select {{
                        padding: 10px;
                        border: 1px solid #ddd;
                        border-radius: 5px;
                    }}
                    button {{
                        padding: 10px 20px;
                        background: #667eea;
                        color: white;
                        border: none;
                        border-radius: 5px;
                        cursor: pointer;
                    }}
                    button:hover {{ background: #5568d3; }}
                    button.secondary {{
                        background: #95a5a6;
                    }}
                    button.secondary:hover {{ background: #7f8c8d; }}
                    table {{
                        width: 100%;
                        border-collapse: collapse;
                        margin-top: 10px;
                    }}
                    th, td {{
                        padding: 12px;
                        text-align: left;
                        border-bottom: 1px solid #e0e0e0;
                    }}
                    th {{ background: #f9f9f9; font-weight: 600; }}
                    .logout-btn {{
                        background: #e74c3c;
                        color: white;
                        border: none;
                        padding: 10px 20px;
                        border-radius: 5px;
                        cursor: pointer;
                        text-decoration: none;
                    }}
                    .month-selector {{
                        display: flex;
                        gap: 10px;
                        margin-bottom: 15px;
                        align-items: center;
                    }}
                    .month-selector select {{
                        padding: 10px;
                        border: 1px solid #ddd;
                        border-radius: 5px;
                    }}
                </style>
            </head>
            <body>
                <div class="header">
                    <h1>📊 Reports & Analytics</h1>
                    <a href="/web/auth/logout" class="logout-btn">Logout</a>
                </div>

                <nav>
                    <a href="/web/dashboard">Dashboard</a>
                    <a href="/web/schedules">Schedules</a>
                    <a href="/web/settings">Settings</a>
                    <a href="/web/reports" class="active">Reports</a>
                </nav>

                <div class="container">
                    <div class="section">
                        <h2>📅 Monthly Statistics - {month_name[today.month]} {today.year}</h2>
                        <div class="month-selector">
                            <label>Select Month:</label>
                            <select id="monthSelect" onchange="loadMonthStats()">
                                <option value="{today.year}-{today.month:02d}">Current Month</option>
                                <option value="custom">Custom Month</option>
                            </select>
                            <input type="month" id="monthInput" style="display:none;" onchange="loadMonthStats()">
                        </div>
                    </div>

                    <div class="stats">
                        <div class="stat-card">
                            <h3>Total Duty Days</h3>
                            <div class="value">{total_duty_days}</div>
                        </div>
                        <div class="stat-card">
                            <h3>Total Shift Days</h3>
                            <div class="value">{total_shift_days}</div>
                        </div>
                        <div class="stat-card">
                            <h3>Records</h3>
                            <div class="value">{total_records}</div>
                        </div>
                    </div>

                    <div class="section">
                        <h2>Top Users by Duty Count</h2>
                        <table>
                            <thead>
                                <tr>
                                    <th>Rank</th>
                                    <th>User</th>
                                    <th>Total Duties</th>
                                </tr>
                            </thead>
                            <tbody>
                                {user_stats_html}
                            </tbody>
                        </table>
                    </div>

                    <div class="section">
                        <h2>Team Workload Distribution</h2>
                        <table>
                            <thead>
                                <tr>
                                    <th>Team</th>
                                    <th>Total Duties</th>
                                    <th>Team Members</th>
                                    <th>Avg per Member</th>
                                </tr>
                            </thead>
                            <tbody>
                                {team_stats_html}
                            </tbody>
                        </table>
                    </div>

                    <div class="section">
                        <h2>📥 Export Reports</h2>
                        <div class="report-controls">
                            <input type="date" id="startDate" value="{(today - timedelta(days=30)).isoformat()}">
                            <input type="date" id="endDate" value="{today.isoformat()}">
                            <select id="reportFormat">
                                <option value="csv">CSV</option>
                                <option value="html">HTML Report</option>
                                <option value="json">JSON</option>
                            </select>
                            <button onclick="generateReport()">📥 Generate Report</button>
                        </div>
                    </div>

                    <div class="section">
                        <h2>Generate Monthly Statistics Report</h2>
                        <div class="report-controls">
                            <input type="month" id="reportMonth" value="{today.year}-{today.month:02d}">
                            <button onclick="generateStatsReport()">📊 Generate Stats Report</button>
                        </div>
                    </div>
                </div>

                <script>
                    function generateReport() {{
                        const startDate = document.getElementById('startDate').value;
                        const endDate = document.getElementById('endDate').value;
                        const format = document.getElementById('reportFormat').value;

                        if (!startDate || !endDate) {{
                            alert('Please select both start and end dates');
                            return;
                        }}

                        window.location.href = `/web/reports/generate?start_date=${{startDate}}&end_date=${{endDate}}&format=${{format}}`;
                    }}

                    function generateStatsReport() {{
                        const monthInput = document.getElementById('reportMonth').value;
                        if (!monthInput) {{
                            alert('Please select a month');
                            return;
                        }}
                        const [year, month] = monthInput.split('-');
                        window.location.href = `/web/reports/stats?year=${{year}}&month=${{month}}`;
                    }}

                    document.getElementById('monthSelect').addEventListener('change', (e) => {{
                        if (e.target.value === 'custom') {{
                            document.getElementById('monthInput').style.display = 'block';
                        }} else {{
                            document.getElementById('monthInput').style.display = 'none';
                        }}
                    }});
                </script>
            </body>
            </html>
            """

            return HTMLResponse(content=html)

    except Exception as e:
        logger.error(f"Error rendering reports page: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/generate")
async def generate_report(
    request: Request,
    start_date: str,
    end_date: str,
    format: str = "csv",
    session: dict = Depends(get_session_from_cookie)
):
    """Generate and download report"""
    try:
        async with AsyncSessionLocal() as db:
            workspace_id = session['workspace_id']

            # Parse dates
            start = datetime.fromisoformat(start_date).date()
            end = datetime.fromisoformat(end_date).date()

            # Get schedules for date range
            stmt = select(Schedule).where(
                (Schedule.date >= start) &
                (Schedule.date <= end)
            ).options(joinedload(Schedule.user), joinedload(Schedule.team))
            result = await db.execute(stmt)
            schedules = result.unique().scalars().all()

            if format == "csv":
                # Generate CSV
                output = io.StringIO()
                writer = csv.writer(output)
                writer.writerow(['Date', 'User', 'Team', 'Notes'])

                for schedule in schedules:
                    writer.writerow([
                        schedule.date,
                        schedule.user.first_name or schedule.user.username,
                        schedule.team.name if schedule.team else '',
                        ''
                    ])

                return StreamingResponse(
                    iter([output.getvalue()]),
                    media_type="text/csv",
                    headers={"Content-Disposition": f"attachment; filename=duty_report_{start}_{end}.csv"}
                )

            elif format == "html":
                # Generate HTML
                rows = ''.join(f'''<tr>
                    <td>{schedule.duty_date}</td>
                    <td>{schedule.user.first_name or schedule.user.username}</td>
                    <td>{schedule.team.name if schedule.team else ''}</td>
                </tr>''' for schedule in schedules)

                html = f"""
                <!DOCTYPE html>
                <html>
                <head>
                    <title>Duty Report {start} to {end}</title>
                    <style>
                        body {{ font-family: Arial, sans-serif; padding: 20px; }}
                        h1 {{ color: #333; }}
                        table {{ border-collapse: collapse; width: 100%; margin-top: 20px; }}
                        th, td {{ border: 1px solid #ddd; padding: 10px; text-align: left; }}
                        th {{ background: #f5f5f5; }}
                    </style>
                </head>
                <body>
                    <h1>Duty Report</h1>
                    <p>Period: {start} to {end}</p>
                    <table>
                        <thead>
                            <tr>
                                <th>Date</th>
                                <th>User</th>
                                <th>Team</th>
                            </tr>
                        </thead>
                        <tbody>
                            {rows if rows else '<tr><td colspan="3">No data</td></tr>'}
                        </tbody>
                    </table>
                </body>
                </html>
                """

                return StreamingResponse(
                    iter([html]),
                    media_type="text/html",
                    headers={"Content-Disposition": f"attachment; filename=duty_report_{start}_{end}.html"}
                )

            elif format == "json":
                # Generate JSON
                import json
                data = {
                    "report": {
                        "start_date": str(start),
                        "end_date": str(end),
                        "total_duties": len(schedules),
                        "schedules": [
                            {
                                "date": str(schedule.duty_date),
                                "user": schedule.user.first_name or schedule.user.username,
                                "team": schedule.team.name if schedule.team else None,
                            }
                            for schedule in schedules
                        ]
                    }
                }

                return StreamingResponse(
                    iter([json.dumps(data, indent=2)]),
                    media_type="application/json",
                    headers={"Content-Disposition": f"attachment; filename=duty_report_{start}_{end}.json"}
                )

    except Exception as e:
        logger.error(f"Error generating report: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/stats")
async def generate_stats_report(
    request: Request,
    year: int,
    month: int,
    format: str = "html",
    session: dict = Depends(get_session_from_cookie)
):
    """Generate statistics report for a specific month"""
    try:
        async with AsyncSessionLocal() as db:
            workspace_id = session['workspace_id']

            # Initialize stats service
            stats_service = StatsService(db)

            if format == "html":
                # Generate HTML report
                html = await stats_service.generate_html_report(
                    workspace_id, year, month
                )
                filename = f"duty_stats_{year}-{month:02d}.html"
                return StreamingResponse(
                    iter([html]),
                    media_type="text/html",
                    headers={"Content-Disposition": f"attachment; filename={filename}"}
                )

            elif format == "csv":
                # Generate CSV report
                csv_content = await stats_service.generate_csv_report(
                    workspace_id, year, month
                )
                filename = f"duty_stats_{year}-{month:02d}.csv"
                return StreamingResponse(
                    iter([csv_content]),
                    media_type="text/csv",
                    headers={"Content-Disposition": f"attachment; filename={filename}"}
                )

            elif format == "json":
                # Generate JSON report
                json_data = await stats_service.generate_json_report(
                    workspace_id, year, month
                )
                filename = f"duty_stats_{year}-{month:02d}.json"
                return StreamingResponse(
                    iter([json.dumps(json_data, indent=2)]),
                    media_type="application/json",
                    headers={"Content-Disposition": f"attachment; filename={filename}"}
                )

            else:
                raise HTTPException(status_code=400, detail="Invalid format")

    except Exception as e:
        logger.error(f"Error generating stats report: {e}")
        raise HTTPException(status_code=500, detail=str(e))
