import logging
from datetime import datetime, date, timedelta, timezone as dt_timezone
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger
from pytz import timezone
from zoneinfo import ZoneInfo
from sqlalchemy import select
from slack_sdk.web.async_client import AsyncWebClient
from telegram import Bot
from app.database import AsyncSessionLocal, get_db_with_retry
from app.commands.handlers import CommandHandler as BotCommandHandler
from app.services.stats_service import StatsService
from app.models import Workspace
from app.config import get_settings
from app.repositories import EscalationRepository, EscalationEventRepository

logger = logging.getLogger(__name__)
settings = get_settings()


class ScheduledTasks:
    def __init__(self, telegram_bot: Bot = None, slack_client: AsyncWebClient = None, telegram_chat_id: int = None, slack_channel_id: str = None):
        self.scheduler = AsyncIOScheduler(timezone=settings.timezone)
        self.telegram_bot = telegram_bot
        self.slack_client = slack_client
        self.telegram_chat_id = telegram_chat_id
        self.slack_channel_id = slack_channel_id

    def setup(self):
        """Setup all scheduled tasks"""
        # Parse digest time (HH:MM format)
        hour, minute = map(int, settings.morning_digest_time.split(':'))

        # Morning digest - every day at configured time
        self.scheduler.add_job(
            self.morning_digest,
            CronTrigger(hour=hour, minute=minute, timezone=settings.timezone),
            id='morning_digest',
            name='Morning duty digest'
        )

        # Check escalations every minute
        self.scheduler.add_job(
            self.check_auto_escalations,
            IntervalTrigger(minutes=1),
            id='check_escalations',
            name='Check auto-escalations'
        )

        # Recalculate statistics on the 1st of every month at 01:00
        self.scheduler.add_job(
            self.recalculate_monthly_stats,
            CronTrigger(day=1, hour=1, minute=0, timezone=settings.timezone),
            id='recalculate_stats',
            name='Recalculate monthly statistics'
        )

        # Sync Google Calendar every 4 hours
        self.scheduler.add_job(
            self.sync_google_calendars,
            IntervalTrigger(hours=4),
            id='sync_google_calendars',
            name='Sync Google Calendar schedules'
        )

    async def start(self):
        """Start scheduler"""
        self.setup()
        self.scheduler.start()
        logger.info("Scheduled tasks started")

    async def stop(self):
        """Stop scheduler"""
        self.scheduler.shutdown()
        logger.info("Scheduled tasks stopped")

    async def get_all_workspaces(self, db) -> list[Workspace]:
        """Get all workspaces from database"""
        stmt = select(Workspace)
        result = await db.execute(stmt)
        return result.scalars().all()

    async def morning_digest(self):
        """Send morning digest with today's duties to all workspaces"""
        try:
            async with get_db_with_retry() as db:
                workspaces = await self.get_all_workspaces(db)

                for workspace in workspaces:
                    try:
                        handler = BotCommandHandler(db, workspace.id)
                        message = await handler.duty_today()

                        # Send to Telegram workspace
                        if workspace.workspace_type == 'telegram' and self.telegram_bot:
                            try:
                                await self.telegram_bot.send_message(
                                    chat_id=int(workspace.external_id),
                                    text=f"📅 *Good morning! Today's duties:*\n\n{message}",
                                    parse_mode='Markdown'
                                )
                                logger.info(f"Morning digest sent to Telegram workspace {workspace.id}")
                            except Exception as e:
                                logger.error(f"Failed to send Telegram digest to workspace {workspace.id}: {e}")

                        # Send to Slack workspace
                        elif workspace.workspace_type == 'slack' and self.slack_client and self.slack_channel_id:
                            try:
                                await self.slack_client.chat_postMessage(
                                    channel=self.slack_channel_id,
                                    text=f"📅 Good morning! Today's duties:\n\n{message}"
                                )
                                logger.info(f"Morning digest sent to Slack workspace {workspace.id}")
                            except Exception as e:
                                logger.error(f"Failed to send Slack digest to workspace {workspace.id}: {e}")

                    except Exception as e:
                        logger.warning(f"Error sending morning digest to workspace {workspace.id}: {e}")

                logger.info("Morning digest sent to all workspaces")

        except Exception as e:
            logger.exception(f"Error in morning_digest: {e}")

    async def send_reminders(self):
        """Send reminders to duty people in all workspaces"""
        try:
            async with get_db_with_retry() as db:
                workspaces = await self.get_all_workspaces(db)
                # Use application's configured timezone for consistent date comparison
                tz = ZoneInfo(settings.timezone)
                today = datetime.now(tz).date()

                for workspace in workspaces:
                    try:
                        handler = BotCommandHandler(db, workspace.id)
                        teams = await handler.team_service.get_all_teams(workspace.id)

                        for team in teams:
                            try:
                                # Get all on-duty people for the team today
                                from app.services.schedule_service import ScheduleService
                                from app.repositories.schedule_repository import ScheduleRepository
                                schedule_service = ScheduleService(ScheduleRepository(db))
                                users = await schedule_service.get_today_duties(team.id, today)

                                for user in users:
                                    if user.telegram_username and self.telegram_bot and workspace.workspace_type == 'telegram':
                                        try:
                                            await self.telegram_bot.send_message(
                                                chat_id=f"@{user.telegram_username}",
                                                text=f"⏰ Reminder: You are on duty for {team.display_name} today"
                                            )
                                        except Exception as e:
                                            logger.warning(f"Failed to send Telegram reminder to {user.display_name}: {e}")

                            except Exception as e:
                                logger.warning(f"Error sending reminders for team {team.display_name} in workspace {workspace.id}: {e}")

                    except Exception as e:
                        logger.warning(f"Error sending reminders for workspace {workspace.id}: {e}")

                logger.info("Reminders sent to all workspaces")

        except Exception as e:
            logger.exception(f"Error in send_reminders: {e}")

    async def check_auto_escalations(self):
        """Check if auto-escalation should be triggered in all workspaces"""
        try:
            async with get_db_with_retry() as db:
                workspaces = await self.get_all_workspaces(db)

                for workspace in workspaces:
                    try:
                        from app.services.escalation_service import EscalationService
                        escalation_repo = EscalationRepository(db)
                        event_repo = EscalationEventRepository(db)
                        escalation_service = EscalationService(escalation_repo, event_repo)
                        handler = BotCommandHandler(db, workspace.id)

                        teams = await handler.team_service.get_all_teams(workspace.id)

                        for team in teams:
                            try:
                                event = await escalation_service.get_active_escalation(team)
                                if not event:
                                    continue

                                # Check if timeout exceeded
                                tz = ZoneInfo(settings.timezone)
                                elapsed = datetime.now(tz) - event.initiated_at
                                timeout = timedelta(minutes=settings.escalation_timeout_minutes)

                                if elapsed > timeout and not event.escalated_to_level2_at:
                                    # Auto-escalate to level 2
                                    await escalation_service.escalate_to_level2(event)

                                    cto = await escalation_service.get_cto(workspace.id)
                                    if not cto:
                                        logger.warning(f"No CTO assigned for auto-escalation in {team.display_name} (workspace {workspace.id})")
                                        continue

                                    mention = f"@{cto.telegram_username or cto.slack_user_id}"
                                    message = f"⚠️ Auto-escalation to Level 2: {team.display_name} issue escalated to {mention}"

                                    # Send to the messenger where escalation was initiated
                                    if event.messenger == 'telegram' and self.telegram_bot:
                                        try:
                                            await self.telegram_bot.send_message(
                                                chat_id=int(workspace.external_id),
                                                text=message,
                                                parse_mode='Markdown'
                                            )
                                            logger.info(f"Auto-escalation message sent to Telegram workspace {workspace.id}")
                                        except Exception as e:
                                            logger.error(f"Failed to send auto-escalation message to Telegram workspace {workspace.id}: {e}")

                                    elif event.messenger == 'slack' and self.slack_client and self.slack_channel_id:
                                        try:
                                            await self.slack_client.chat_postMessage(
                                                channel=self.slack_channel_id,
                                                text=message
                                            )
                                            logger.info(f"Auto-escalation message sent to Slack workspace {workspace.id}")
                                        except Exception as e:
                                            logger.error(f"Failed to send auto-escalation message to Slack workspace {workspace.id}: {e}")

                                    logger.info(f"Auto-escalated {team.display_name} to level 2 in workspace {workspace.id}")

                            except Exception as e:
                                logger.warning(f"Error checking escalations for team {team.display_name} in workspace {workspace.id}: {e}")

                    except Exception as e:
                        logger.warning(f"Error checking escalations for workspace {workspace.id}: {e}")

        except Exception as e:
            logger.exception(f"Error in check_auto_escalations: {e}")

    async def recalculate_monthly_stats(self):
        """Recalculate statistics for the previous month in all workspaces"""
        try:
            async with get_db_with_retry() as db:
                workspaces = await self.get_all_workspaces(db)

                # Calculate previous month
                tz = ZoneInfo(settings.timezone)
                today = datetime.now(tz).date()
                # If today is the 1st, calculate for previous month
                # Otherwise calculate for the month before previous
                if today.day == 1:
                    target_date = today - timedelta(days=1)
                else:
                    target_date = today - timedelta(days=today.day)

                year = target_date.year
                month = target_date.month

                for workspace in workspaces:
                    try:
                        stats_service = StatsService(db)
                        stats = await stats_service.recalculate_stats(workspace.id, year, month)
                        logger.info(f"Recalculated {len(stats)} statistics records for workspace {workspace.id} ({year}-{month:02d})")
                    except Exception as e:
                        logger.warning(f"Error recalculating stats for workspace {workspace.id}: {e}")

                logger.info(f"Monthly statistics recalculation completed for {year}-{month:02d}")

        except Exception as e:
            logger.exception(f"Error in recalculate_monthly_stats: {e}")

    async def sync_google_calendars(self):
        """Sync Google Calendar schedules for all workspaces"""
        try:
            async with get_db_with_retry() as db:
                workspaces = await self.get_all_workspaces(db)

                for workspace in workspaces:
                    try:
                        from app.services.google_calendar_service import GoogleCalendarService
                        from app.repositories.google_calendar_repository import GoogleCalendarRepository
                        from app.repositories.schedule_repository import ScheduleRepository
                        from app.repositories.team_repository import TeamRepository

                        google_calendar_repo = GoogleCalendarRepository(db)
                        schedule_repo = ScheduleRepository(db)
                        team_repo = TeamRepository(db)
                        google_calendar_service = GoogleCalendarService(google_calendar_repo)

                        synced_count = await google_calendar_service.sync_workspace_schedules(
                            workspace.id,
                            schedule_repo,
                            team_repo
                        )

                        logger.info(f"Google Calendar sync completed for workspace {workspace.id}: {synced_count} events synced")

                    except Exception as e:
                        logger.warning(f"Error syncing Google Calendar for workspace {workspace.id}: {e}")

                logger.info("Google Calendar sync completed for all workspaces")

        except Exception as e:
            logger.exception(f"Error in sync_google_calendars: {e}")
