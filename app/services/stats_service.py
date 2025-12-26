"""Service for duty statistics and reports generation"""
from datetime import date, datetime
from dateutil.relativedelta import relativedelta
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, func
from sqlalchemy.orm import selectinload

from app.models import DutyStats, Schedule, User, Team, Workspace
from app.repositories import DutyStatsRepository


class StatsService:
    """Handle duty statistics calculation and reporting"""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.stats_repo = DutyStatsRepository(db)

    async def recalculate_stats(
        self, workspace_id: int, year: int, month: int
    ) -> list[DutyStats]:
        """
        Recalculate statistics for a given month across all teams and users.

        Returns list of DutyStats records created/updated.
        """
        # Calculate date range for the month
        start_date = date(year, month, 1)
        end_date = (start_date + relativedelta(months=1)) - relativedelta(days=1)

        # Single aggregated query: GROUP BY team_id, user_id, is_shift
        # This replaces 1000+ individual queries with 1 efficient query
        result = await self.db.execute(
            select(
                Schedule.team_id,
                Schedule.user_id,
                Schedule.is_shift,
                func.count(Schedule.id).label("count")
            )
            .where(
                and_(
                    Schedule.date >= start_date,
                    Schedule.date <= end_date,
                    Team.workspace_id == workspace_id
                )
            )
            .join(Team, Schedule.team_id == Team.id)
            .group_by(Schedule.team_id, Schedule.user_id, Schedule.is_shift)
        )

        # Build stats dictionary: {(team_id, user_id): {'duty_days': X, 'shift_days': Y}}
        stats_data = {}
        for row in result.all():
            team_id, user_id, is_shift, count = row
            key = (team_id, user_id)
            if key not in stats_data:
                stats_data[key] = {'team_id': team_id, 'user_id': user_id, 'duty_days': 0, 'shift_days': 0}

            if is_shift:
                stats_data[key]['shift_days'] = count
            else:
                stats_data[key]['duty_days'] = count

        # Convert to list and batch update all records
        stats_list = list(stats_data.values())
        await self.stats_repo.batch_update_stats(workspace_id, year, month, stats_list)

        # Fetch and return updated records
        return await self.stats_repo.get_workspace_monthly_stats(workspace_id, year, month)

    async def get_user_monthly_stats(
        self, workspace_id: int, user_id: int, year: int, month: int
    ) -> list[DutyStats]:
        """Get monthly statistics for a specific user across all teams"""
        return await self.stats_repo.get_user_monthly_stats(workspace_id, user_id, year, month)

    async def get_team_monthly_stats(
        self, workspace_id: int, team_id: int, year: int, month: int
    ) -> list[DutyStats]:
        """Get monthly statistics for a specific team across all users"""
        return await self.stats_repo.get_team_monthly_stats(workspace_id, team_id, year, month)

    async def get_workspace_monthly_stats(
        self, workspace_id: int, year: int, month: int
    ) -> list[DutyStats]:
        """Get all statistics for workspace in a given month"""
        return await self.stats_repo.get_workspace_monthly_stats(workspace_id, year, month)

    async def get_user_annual_stats(
        self, workspace_id: int, user_id: int, year: int
    ) -> list[DutyStats]:
        """Get annual statistics for a user"""
        return await self.stats_repo.get_user_annual_stats(workspace_id, user_id, year)

    async def get_team_annual_stats(
        self, workspace_id: int, team_id: int, year: int
    ) -> list[DutyStats]:
        """Get annual statistics for a team"""
        return await self.stats_repo.get_team_annual_stats(workspace_id, team_id, year)

    async def get_top_users_by_duties(
        self, workspace_id: int, year: int, month: int, limit: int = 10
    ) -> list[dict]:
        """Get top users by duty count in a month"""
        return await self.stats_repo.get_top_users_by_duties(workspace_id, year, month, limit)

    async def get_team_workload(
        self, workspace_id: int, year: int, month: int
    ) -> list[dict]:
        """Get workload distribution across teams"""
        return await self.stats_repo.get_team_workload(workspace_id, year, month)

    async def generate_html_report(
        self,
        workspace_id: int,
        year: int,
        month: int,
        start_date: date = None,
        end_date: date = None,
    ) -> str:
        """Generate HTML report for duty statistics"""
        from calendar import month_name

        if not start_date:
            start_date = date(year, month, 1)
        if not end_date:
            end_date = (start_date + relativedelta(months=1)) - relativedelta(days=1)

        stats = await self.get_workspace_monthly_stats(workspace_id, year, month)
        top_users = await self.get_top_users_by_duties(workspace_id, year, month, 10)
        team_workload = await self.get_team_workload(workspace_id, year, month)

        # Group stats by team
        stats_by_team = {}
        for stat in stats:
            if stat.team_id not in stats_by_team:
                stats_by_team[stat.team_id] = {
                    "team_name": stat.team.display_name,
                    "users": [],
                }
            stats_by_team[stat.team_id]["users"].append(
                {
                    "user_name": stat.user.display_name,
                    "duty_days": stat.duty_days,
                    "shift_days": stat.shift_days,
                }
            )

        html = f"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Duty Statistics Report - {month_name[month]} {year}</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 20px; background-color: #f5f5f5; }}
        .container {{ max-width: 1200px; margin: 0 auto; background-color: white; padding: 20px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }}
        h1 {{ color: #333; text-align: center; border-bottom: 3px solid #007bff; padding-bottom: 10px; }}
        h2 {{ color: #555; margin-top: 30px; border-left: 4px solid #007bff; padding-left: 10px; }}
        .summary {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 15px; margin: 20px 0; }}
        .stat-box {{ background-color: #f9f9f9; border: 1px solid #ddd; padding: 15px; border-radius: 5px; text-align: center; }}
        .stat-box h3 {{ margin: 0; color: #007bff; font-size: 24px; }}
        .stat-box p {{ margin: 5px 0 0 0; color: #666; }}
        table {{ width: 100%; border-collapse: collapse; margin: 15px 0; }}
        th {{ background-color: #007bff; color: white; padding: 12px; text-align: left; }}
        td {{ padding: 10px 12px; border-bottom: 1px solid #ddd; }}
        tr:hover {{ background-color: #f9f9f9; }}
    </style>
</head>
<body>
    <div class="container">
        <h1>Duty Statistics Report</h1>
        <p style="text-align: center; color: #666;">
            <strong>Period:</strong> {start_date.strftime('%B %d, %Y')} - {end_date.strftime('%B %d, %Y')}
        </p>

        <h2>Summary</h2>
        <div class="summary">
            <div class="stat-box">
                <h3>{len(stats)}</h3>
                <p>Total Records</p>
            </div>
            <div class="stat-box">
                <h3>{len(set(s.user_id for s in stats))}</h3>
                <p>Unique Users</p>
            </div>
            <div class="stat-box">
                <h3>{sum(s.duty_days for s in stats)}</h3>
                <p>Total Duty Days</p>
            </div>
            <div class="stat-box">
                <h3>{sum(s.shift_days for s in stats)}</h3>
                <p>Total Shift Days</p>
            </div>
        </div>

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
"""
        for rank, user in enumerate(top_users, 1):
            html += f"""
                <tr>
                    <td>{rank}</td>
                    <td>{user['display_name']}</td>
                    <td>{user['total_duties']}</td>
                </tr>
"""
        html += """
            </tbody>
        </table>

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
"""
        for team in team_workload:
            avg_duties = (
                team["total_duties"] / team["team_members"]
                if team["team_members"] > 0
                else 0
            )
            html += f"""
                <tr>
                    <td>{team['team_name']}</td>
                    <td>{team['total_duties']}</td>
                    <td>{team['team_members']}</td>
                    <td>{avg_duties:.1f}</td>
                </tr>
"""
        html += """
            </tbody>
        </table>

        <h2>Detailed Statistics by Team</h2>
"""
        for team_id, team_data in stats_by_team.items():
            html += f"""
        <h3>{team_data['team_name']}</h3>
        <table>
            <thead>
                <tr>
                    <th>User</th>
                    <th>Duty Days</th>
                    <th>Shift Days</th>
                </tr>
            </thead>
            <tbody>
"""
            for user in team_data["users"]:
                html += f"""
                <tr>
                    <td>{user['user_name']}</td>
                    <td>{user['duty_days']}</td>
                    <td>{user['shift_days']}</td>
                </tr>
"""
            html += """
            </tbody>
        </table>
"""

        html += f"""
        <div style="margin-top: 30px; text-align: center; color: #666; font-size: 12px; border-top: 1px solid #ddd; padding-top: 15px;">
            <p>Report generated on {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')} UTC</p>
        </div>
    </div>
</body>
</html>
"""
        return html

    async def generate_csv_report(
        self, workspace_id: int, year: int, month: int
    ) -> str:
        """Generate CSV report for duty statistics"""
        stats = await self.get_workspace_monthly_stats(workspace_id, year, month)

        csv_lines = [
            "Date,Team,User,Duty Days,Shift Days",
        ]

        for stat in stats:
            csv_lines.append(
                f"{year}-{month:02d},\"{stat.team.display_name}\",\"{stat.user.display_name}\",{stat.duty_days},{stat.shift_days}"
            )

        return "\n".join(csv_lines)

    async def generate_json_report(
        self, workspace_id: int, year: int, month: int
    ) -> dict:
        """Generate JSON report for duty statistics"""
        stats = await self.get_workspace_monthly_stats(workspace_id, year, month)
        top_users = await self.get_top_users_by_duties(workspace_id, year, month)
        team_workload = await self.get_team_workload(workspace_id, year, month)

        return {
            "report": {
                "period": f"{year}-{month:02d}",
                "total_duty_days": sum(s.duty_days for s in stats),
                "total_shift_days": sum(s.shift_days for s in stats),
                "stats": [
                    {
                        "team": stat.team.display_name,
                        "user": stat.user.display_name,
                        "duty_days": stat.duty_days,
                        "shift_days": stat.shift_days,
                    }
                    for stat in stats
                ],
                "top_users": top_users,
                "team_workload": team_workload,
            }
        }
