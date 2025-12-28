"""Report generation routes for web admin panel"""
import logging
import csv
import io
import json
from datetime import datetime, timedelta, date
from calendar import month_name
from fastapi import APIRouter, Request, HTTPException, Depends
from fastapi.responses import HTMLResponse, StreamingResponse, RedirectResponse
from sqlalchemy import select, func, and_
from sqlalchemy.orm import joinedload

from app.database import AsyncSessionLocal
from app.models import Schedule, User, Team, AdminLog, Workspace, DutyStats
from app.services.stats_service import StatsService
from app.auth import session_manager

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/web/reports", tags=["reports"])
api_router = APIRouter(prefix="/api/reports", tags=["reports"])


def get_session_from_cookie(request: Request):
    """Extract and validate session from cookies or Authorization header"""
    token = request.cookies.get('session_token')
    
    # Also check Authorization header for flexibility (used by React app)
    if not token:
        auth_header = request.headers.get("Authorization")
        if auth_header and auth_header.startswith("Bearer "):
            token = auth_header.split(" ", 1)[1]

    if not token:
        raise HTTPException(status_code=401, detail="Not authenticated")

    session = session_manager.validate_session(token)
    if not session:
        raise HTTPException(status_code=401, detail="Invalid or expired session")

    return session


@router.get("")
async def reports_page(request: Request, session: dict = Depends(get_session_from_cookie)):
    """Reports page - Redirect to modern React dashboard"""
    return RedirectResponse(url="/reports")


@router.get("/generate")
@api_router.get("/generate")
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
            stmt = select(Schedule).join(Schedule.team).where(
                (Team.workspace_id == workspace_id) &
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
                    <td>{schedule.date}</td>
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
                                "date": str(schedule.date),
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
@api_router.get("/stats")
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
