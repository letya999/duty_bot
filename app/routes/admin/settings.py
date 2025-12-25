"""Settings and configuration routes for web admin panel"""
import logging
from fastapi import APIRouter, Request, HTTPException, Depends, Form
from fastapi.responses import HTMLResponse
from sqlalchemy import select
from sqlalchemy.orm import joinedload

from app.database import AsyncSessionLocal
from app.models import User, Workspace
from app.config import get_settings
from app.auth import session_manager
from app.services.admin_service import AdminService

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/web/settings", tags=["settings"])
settings = get_settings()


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
async def settings_page(request: Request, session: dict = Depends(get_session_from_cookie)):
    """Settings and configuration page"""
    try:
        async with AsyncSessionLocal() as db:
            workspace_id = session['workspace_id']
            user_id = session['user_id']

            # Get current user
            current_user = await db.get(User, user_id)

            # Check if user is admin
            is_admin = current_user.is_admin if current_user else False

            if not is_admin:
                raise HTTPException(status_code=403, detail="Only admins can access settings")

            # Get workspace
            workspace = await db.get(Workspace, workspace_id)

            # Get all admins
            stmt = select(User).where(
                (User.workspace_id == workspace_id) &
                (User.is_admin == True)
            )
            result = await db.execute(stmt)
            admins = result.scalars().all()

            # Get all users
            stmt = select(User).where(User.workspace_id == workspace_id)
            result = await db.execute(stmt)
            all_users = result.scalars().all()

            # Generate admin options
            admin_options = ''.join(
                f'<option value="{admin.id}">{admin.first_name or admin.username}</option>'
                for admin in admins
            )

            user_options = ''.join(
                f'<tr><td>{user.first_name or user.username}</td><td>{"✓" if user.is_admin else "✗"}</td><td>'
                f'<button onclick="promoteUser({user.id})">Make Admin</button> '
                f'<button onclick="demoteUser({user.id})">Remove Admin</button>'
                f'</td></tr>'
                for user in all_users
            )

            html = f"""
            <!DOCTYPE html>
            <html>
            <head>
                <title>Settings - Duty Bot</title>
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
                        max-width: 1000px;
                        margin: 20px auto;
                        padding: 0 20px;
                    }}
                    .section {{
                        background: white;
                        padding: 20px;
                        border-radius: 8px;
                        margin-bottom: 20px;
                        box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
                    }}
                    .section h2 {{
                        margin-bottom: 15px;
                        color: #333;
                        border-bottom: 2px solid #667eea;
                        padding-bottom: 10px;
                    }}
                    label {{
                        display: block;
                        margin-bottom: 5px;
                        font-weight: 500;
                        color: #333;
                    }}
                    input[type="text"], input[type="number"], select, textarea {{
                        width: 100%;
                        padding: 10px;
                        margin-bottom: 15px;
                        border: 1px solid #ddd;
                        border-radius: 5px;
                        font-size: 14px;
                    }}
                    button {{
                        padding: 10px 20px;
                        background: #667eea;
                        color: white;
                        border: none;
                        border-radius: 5px;
                        cursor: pointer;
                        margin-right: 10px;
                    }}
                    button:hover {{ background: #5568d3; }}
                    button.danger {{
                        background: #e74c3c;
                    }}
                    button.danger:hover {{ background: #c0392b; }}
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
                </style>
            </head>
            <body>
                <div class="header">
                    <h1>⚙️ Settings & Configuration</h1>
                    <a href="/web/auth/logout" class="logout-btn">Logout</a>
                </div>

                <nav>
                    <a href="/web/dashboard">Dashboard</a>
                    <a href="/web/schedules">Schedules</a>
                    <a href="/web/settings" class="active">Settings</a>
                    <a href="/web/reports">Reports</a>
                </nav>

                <div class="container">
                    <div class="section">
                        <h2>Admin Management</h2>
                        <p>Current admins in this workspace: <strong>{len(admins)}</strong></p>
                        <table>
                            <thead>
                                <tr>
                                    <th>User</th>
                                    <th>Admin</th>
                                    <th>Actions</th>
                                </tr>
                            </thead>
                            <tbody>
                                {user_options if user_options else '<tr><td colspan="3">No users found</td></tr>'}
                            </tbody>
                        </table>
                    </div>

                    <div class="section">
                        <h2>Workspace Settings</h2>
                        <label>Workspace Name</label>
                        <input type="text" id="workspaceName" value="{workspace.name if workspace else ''}" readonly>

                        <label>Platform</label>
                        <input type="text" id="platform" value="{workspace.platform if workspace else ''}" readonly>

                        <label>Work Hours Start (24h format)</label>
                        <input type="number" id="workHoursStart" min="0" max="23" value="9" placeholder="9">

                        <label>Work Hours End (24h format)</label>
                        <input type="number" id="workHoursEnd" min="0" max="23" value="18" placeholder="18">

                        <label>Auto-rotation Enabled</label>
                        <select id="autoRotation">
                            <option value="true">Yes</option>
                            <option value="false">No</option>
                        </select>

                        <label>Rotation Interval (days)</label>
                        <input type="number" id="rotationInterval" min="1" max="30" value="7">

                        <button onclick="saveSettings()">💾 Save Settings</button>
                    </div>

                    <div class="section">
                        <h2>Holiday & Time Off</h2>
                        <label>Add Holiday</label>
                        <input type="date" id="holidayDate">
                        <input type="text" id="holidayName" placeholder="Holiday name">
                        <button onclick="addHoliday()">➕ Add Holiday</button>

                        <h3 style="margin-top: 20px;">Holiday List</h3>
                        <table>
                            <thead>
                                <tr>
                                    <th>Date</th>
                                    <th>Name</th>
                                    <th>Actions</th>
                                </tr>
                            </thead>
                            <tbody id="holidayList">
                                <tr><td colspan="3">No holidays configured</td></tr>
                            </tbody>
                        </table>
                    </div>

                    <div class="section">
                        <h2>Notification Settings</h2>
                        <label>Enable Morning Digest</label>
                        <select id="morningDigest">
                            <option value="true">Yes</option>
                            <option value="false">No</option>
                        </select>

                        <label>Digest Time (24h format)</label>
                        <input type="time" id="digestTime" value="09:00">

                        <label>Enable Escalation Alerts</label>
                        <select id="escalationAlerts">
                            <option value="true">Yes</option>
                            <option value="false">No</option>
                        </select>

                        <button onclick="saveNotifications()">💾 Save Notifications</button>
                    </div>
                </div>

                <script>
                    function saveSettings() {{
                        const settings = {{
                            work_hours_start: parseInt(document.getElementById('workHoursStart').value),
                            work_hours_end: parseInt(document.getElementById('workHoursEnd').value),
                            auto_rotation: document.getElementById('autoRotation').value === 'true',
                            rotation_interval: parseInt(document.getElementById('rotationInterval').value)
                        }};

                        fetch('/api/miniapp/settings', {{
                            method: 'POST',
                            headers: {{'Content-Type': 'application/json'}},
                            body: JSON.stringify(settings)
                        }}).then(r => r.json()).then(data => {{
                            if (data.success) {{
                                alert('Settings saved successfully!');
                            }} else {{
                                alert('Error: ' + data.detail);
                            }}
                        }}).catch(e => alert('Error: ' + e.message));
                    }}

                    function addHoliday() {{
                        const date = document.getElementById('holidayDate').value;
                        const name = document.getElementById('holidayName').value;

                        if (!date || !name) {{
                            alert('Please fill in all fields');
                            return;
                        }}

                        fetch('/api/miniapp/holidays', {{
                            method: 'POST',
                            headers: {{'Content-Type': 'application/json'}},
                            body: JSON.stringify({{ date: date, name: name }})
                        }}).then(r => r.json()).then(data => {{
                            if (data.success) {{
                                alert('Holiday added!');
                                document.getElementById('holidayDate').value = '';
                                document.getElementById('holidayName').value = '';
                                location.reload();
                            }} else {{
                                alert('Error: ' + data.detail);
                            }}
                        }}).catch(e => alert('Error: ' + e.message));
                    }}

                    function saveNotifications() {{
                        const settings = {{
                            morning_digest: document.getElementById('morningDigest').value === 'true',
                            digest_time: document.getElementById('digestTime').value,
                            escalation_alerts: document.getElementById('escalationAlerts').value === 'true'
                        }};

                        fetch('/api/miniapp/notifications', {{
                            method: 'POST',
                            headers: {{'Content-Type': 'application/json'}},
                            body: JSON.stringify(settings)
                        }}).then(r => r.json()).then(data => {{
                            if (data.success) {{
                                alert('Notification settings saved!');
                            }} else {{
                                alert('Error: ' + data.detail);
                            }}
                        }}).catch(e => alert('Error: ' + e.message));
                    }}

                    function promoteUser(userId) {{
                        if (confirm('Make this user an admin?')) {{
                            fetch(`/api/miniapp/users/${{userId}}/promote`, {{
                                method: 'POST',
                                headers: {{'Content-Type': 'application/json'}}
                            }}).then(r => r.json()).then(data => {{
                                if (data.success) {{
                                    alert('User promoted to admin!');
                                    location.reload();
                                }} else {{
                                    alert('Error: ' + data.detail);
                                }}
                            }}).catch(e => alert('Error: ' + e.message));
                        }}
                    }}

                    function demoteUser(userId) {{
                        if (confirm('Remove admin status from this user?')) {{
                            fetch(`/api/miniapp/users/${{userId}}/demote`, {{
                                method: 'POST',
                                headers: {{'Content-Type': 'application/json'}}
                            }}).then(r => r.json()).then(data => {{
                                if (data.success) {{
                                    alert('User demoted!');
                                    location.reload();
                                }} else {{
                                    alert('Error: ' + data.detail);
                                }}
                            }}).catch(e => alert('Error: ' + e.message));
                        }}
                    }}
                </script>
            </body>
            </html>
            """

            return HTMLResponse(content=html)

    except Exception as e:
        logger.error(f"Error rendering settings page: {e}")
        raise HTTPException(status_code=500, detail=str(e))
