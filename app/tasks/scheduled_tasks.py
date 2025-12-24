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
from app.services.escalation_service import EscalationService
from app.models import Workspace
from app.config import get_settings

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
                                if team.has_shifts:
                                    shift = await handler.shift_service.get_today_shift(team, today)
                                    users = shift.users if shift else []
                                else:
                                    user = await handler.schedule_service.get_today_duty(team, today)
                                    users = [user] if user else []

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
                        escalation_service = EscalationService(db)
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
