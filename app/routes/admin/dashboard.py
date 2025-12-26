"""Dashboard routes for web admin panel"""
import logging
from datetime import datetime, timedelta
from fastapi import APIRouter, Request, HTTPException, Depends
from fastapi.responses import HTMLResponse
from sqlalchemy import select, func
from sqlalchemy.orm import joinedload

from app.database import AsyncSessionLocal
from app.models import User, Team, Schedule, AdminLog, Workspace
from app.auth import session_manager

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/web/dashboard", tags=["dashboard"])


def get_session_from_cookie(request: Request):
    """Extract and validate session from cookies"""
    token = request.cookies.get('session_token')
    if not token:
        logger.warning("Dashboard access attempted without session token")
        raise HTTPException(status_code=401, detail="Not authenticated")

    session = session_manager.validate_session(token)
    if not session:
        logger.warning(f"Invalid or expired session token: {token[:20]}...")
        raise HTTPException(status_code=401, detail="Invalid or expired session")

    logger.debug(f"Valid session found: user_id={session['user_id']}, workspace_id={session['workspace_id']}")
    return session


@router.get("")
async def dashboard_page(request: Request, session: dict = Depends(get_session_from_cookie)):
    """Main dashboard page"""
    try:
        logger.info(f"Dashboard accessed by user {session['user_id']} in workspace {session['workspace_id']}")
        async with AsyncSessionLocal() as db:
            workspace_id = session['workspace_id']

            # Get current duties (today) - ONLY from this workspace
            today = datetime.now().date()
            stmt = select(Schedule).join(Schedule.team).where(
                (Schedule.date == today) &
                (Team.workspace_id == workspace_id)
            ).options(joinedload(Schedule.team)).options(joinedload(Schedule.user))
            result = await db.execute(stmt)
            today_schedules = result.unique().scalars().all()

            # Get upcoming shifts (next 7 days) - ONLY from this workspace
            start_date = today
            end_date = today + timedelta(days=7)
            stmt = select(Schedule).join(Schedule.team).where(
                (Schedule.date >= start_date) &
                (Schedule.date <= end_date) &
                (Schedule.is_shift == True) &
                (Team.workspace_id == workspace_id)
            ).options(joinedload(Schedule.team)).options(joinedload(Schedule.user))
            result = await db.execute(stmt)
            upcoming_shifts = result.unique().scalars().all()

            # Get teams count
            stmt = select(func.count(Team.id)).where(Team.workspace_id == workspace_id)
            result = await db.execute(stmt)
            teams_count = result.scalar() or 0

            # Get users count
            stmt = select(func.count(User.id)).where(User.workspace_id == workspace_id)
            result = await db.execute(stmt)
            users_count = result.scalar() or 0

            # Get recent admin logs
            stmt = select(AdminLog).where(
                AdminLog.workspace_id == workspace_id
            ).order_by(
                AdminLog.timestamp.desc()
            ).limit(10).options(
                joinedload(AdminLog.admin_user),
                joinedload(AdminLog.target_user)
            )
            result = await db.execute(stmt)
            recent_actions = result.unique().scalars().all()

            # Get current user
            current_user = await db.get(User, session['user_id'])

            html = f"""
            <!DOCTYPE html>
            <html>
            <head>
                <title>Admin Dashboard - Duty Bot</title>
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
                    .header h1 {{ font-size: 24px; }}
                    .user-info {{
                        display: flex;
                        align-items: center;
                        gap: 15px;
                    }}
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
                    table {{
                        width: 100%;
                        border-collapse: collapse;
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
                    .logout-btn:hover {{ background: #c0392b; }}
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
                    nav a:hover {{ color: #333; }}
                    nav a.active {{ color: #667eea; border-bottom: 2px solid #667eea; padding-bottom: 5px; }}
                </style>
            </head>
            <body>
                <div class="header">
                    <h1>🎯 Duty Bot Admin Dashboard</h1>
                    <div class="user-info">
                        <span>{current_user.first_name or current_user.username or 'User'}</span>
                        <a href="/web/auth/logout" class="logout-btn">Logout</a>
                    </div>
                </div>

                <nav>
                    <a href="/web/dashboard" class="active">Dashboard</a>
                    <a href="/web/schedules">Schedules</a>
                    <a href="/web/settings">Settings</a>
                    <a href="/web/reports">Reports</a>
                </nav>

                <div class="container">
                    <div class="stats">
                        <div class="stat-card">
                            <h3>Total Teams</h3>
                            <div class="value">{teams_count}</div>
                        </div>
                        <div class="stat-card">
                            <h3>Total Users</h3>
                            <div class="value">{users_count}</div>
                        </div>
                        <div class="stat-card">
                            <h3>On Duty Today</h3>
                            <div class="value">{len(today_schedules)}</div>
                        </div>
                        <div class="stat-card">
                            <h3>Upcoming Shifts</h3>
                            <div class="value">{len(upcoming_shifts)}</div>
                        </div>
                    </div>

                    <div class="section">
                        <h2>Current Duties (Today)</h2>
                        <table>
                            <thead>
                                <tr>
                                    <th>User</th>
                                    <th>Date</th>
                                    <th>Team</th>
                                </tr>
                            </thead>
                            <tbody>
                                {"".join(f'''
                                <tr>
                                    <td>{schedule.user.first_name or schedule.user.username}</td>
                                    <td>{schedule.date}</td>
                                    <td>{schedule.team.name if schedule.team else "N/A"}</td>
                                </tr>
                                ''' for schedule in today_schedules) if today_schedules else '<tr><td colspan="3" style="text-align: center;">No duties today</td></tr>'}
                            </tbody>
                        </table>
                    </div>

                    <div class="section">
                        <h2>Upcoming Shifts (Next 7 Days)</h2>
                        <table>
                            <thead>
                                <tr>
                                    <th>User</th>
                                    <th>Date</th>
                                    <th>Team</th>
                                </tr>
                            </thead>
                            <tbody>
                                {"".join(f'''
                                <tr>
                                    <td>{schedule.user.first_name or schedule.user.username}</td>
                                    <td>{schedule.date}</td>
                                    <td>{schedule.team.name if schedule.team else "N/A"}</td>
                                </tr>
                                ''' for schedule in upcoming_shifts) if upcoming_shifts else '<tr><td colspan="3" style="text-align: center;">No upcoming shifts</td></tr>'}
                            </tbody>
                        </table>
                    </div>

                    <div class="section">
                        <h2>Recent Admin Actions</h2>
                        <table>
                            <thead>
                                <tr>
                                    <th>Admin</th>
                                    <th>Action</th>
                                    <th>Target User</th>
                                    <th>Timestamp</th>
                                </tr>
                            </thead>
                            <tbody>
                                {"".join(f'''
                                <tr>
                                    <td>{log.admin_user.first_name or log.admin_user.username}</td>
                                    <td>{log.action}</td>
                                    <td>{log.target_user.first_name or log.target_user.username if log.target_user else "N/A"}</td>
                                    <td>{log.timestamp.strftime("%Y-%m-%d %H:%M:%S")}</td>
                                </tr>
                                ''' for log in recent_actions) if recent_actions else '<tr><td colspan="4" style="text-align: center;">No admin actions yet</td></tr>'}
                            </tbody>
                        </table>
                    </div>
                </div>
            </body>
            </html>
            """

            return HTMLResponse(content=html)

    except Exception as e:
        logger.error(f"Error rendering dashboard: {e}")
        raise HTTPException(status_code=500, detail=str(e))
