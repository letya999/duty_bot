import logging
from datetime import datetime, date, timedelta
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger
from pytz import timezone
from slack_sdk.web import WebClient
from telegram import Bot
from app.database import AsyncSessionLocal
from app.commands.handlers import CommandHandler
from app.services.escalation_service import EscalationService
from app.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


class ScheduledTasks:
    def __init__(self, telegram_bot: Bot = None, slack_client: WebClient = None, telegram_chat_id: int = None, slack_channel_id: str = None):
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

    async def morning_digest(self):
        """Send morning digest with today's duties"""
        try:
            async with AsyncSessionLocal() as db:
                handler = CommandHandler(db)
                today = date.today()
                message = await handler.duty_today()

                # Send to Telegram
                if self.telegram_bot and self.telegram_chat_id:
                    try:
                        await self.telegram_bot.send_message(
                            chat_id=self.telegram_chat_id,
                            text=f"📅 *Today's Duties*\n\n{message}",
                            parse_mode='Markdown'
                        )
                    except Exception as e:
                        logger.error(f"Failed to send Telegram digest: {e}")

                # Send to Slack
                if self.slack_client and self.slack_channel_id:
                    try:
                        self.slack_client.chat_postMessage(
                            channel=self.slack_channel_id,
                            text=f"📅 Today's Duties\n\n{message}"
                        )
                    except Exception as e:
                        logger.error(f"Failed to send Slack digest: {e}")

                logger.info("Morning digest sent")

        except Exception as e:
            logger.exception(f"Error in morning_digest: {e}")

    async def send_reminders(self):
        """Send reminders to duty people"""
        try:
            async with AsyncSessionLocal() as db:
                handler = CommandHandler(db)
                today = date.today()

                teams = (await handler.team_service.get_all_teams())

                for team in teams:
                    try:
                        if team.has_shifts:
                            shift = await handler.shift_service.get_today_shift(team, today)
                            users = shift.users if shift else []
                        else:
                            user = await handler.schedule_service.get_today_duty(team, today)
                            users = [user] if user else []

                        for user in users:
                            if user.telegram_username and self.telegram_bot:
                                try:
                                    await self.telegram_bot.send_message(
                                        chat_id=f"@{user.telegram_username}",
                                        text=f"⏰ Reminder: You are on duty for {team.display_name} today"
                                    )
                                except Exception as e:
                                    logger.warning(f"Failed to send Telegram reminder to {user.display_name}: {e}")

                    except Exception as e:
                        logger.warning(f"Error sending reminders for team {team.display_name}: {e}")

                logger.info("Reminders sent")

        except Exception as e:
            logger.exception(f"Error in send_reminders: {e}")

    async def check_auto_escalations(self):
        """Check if auto-escalation should be triggered"""
        try:
            async with AsyncSessionLocal() as db:
                escalation_service = EscalationService(db)
                handler = CommandHandler(db)

                teams = (await handler.team_service.get_all_teams())

                for team in teams:
                    try:
                        event = await escalation_service.get_active_escalation(team)
                        if not event:
                            continue

                        # Check if timeout exceeded
                        elapsed = datetime.utcnow() - event.initiated_at
                        timeout = timedelta(minutes=settings.escalation_timeout_minutes)

                        if elapsed > timeout and not event.escalated_to_level2_at:
                            # Auto-escalate to level 2
                            await escalation_service.escalate_to_level2(event)

                            cto = await escalation_service.get_cto()
                            if not cto:
                                logger.warning(f"No CTO assigned for auto-escalation in {team.display_name}")
                                continue

                            mention = f"@{cto.telegram_username or cto.slack_user_id}"
                            message = f"⚠️ Auto-escalation to Level 2: {team.display_name} issue escalated to {mention}"

                            # Send to the messenger where escalation was initiated
                            if event.messenger == 'telegram' and self.telegram_bot and self.telegram_chat_id:
                                try:
                                    await self.telegram_bot.send_message(
                                        chat_id=self.telegram_chat_id,
                                        text=message,
                                        parse_mode='Markdown'
                                    )
                                except Exception as e:
                                    logger.error(f"Failed to send auto-escalation message to Telegram: {e}")

                            elif event.messenger == 'slack' and self.slack_client and self.slack_channel_id:
                                try:
                                    self.slack_client.chat_postMessage(
                                        channel=self.slack_channel_id,
                                        text=message
                                    )
                                except Exception as e:
                                    logger.error(f"Failed to send auto-escalation message to Slack: {e}")

                            logger.info(f"Auto-escalated {team.display_name} to level 2")

                    except Exception as e:
                        logger.warning(f"Error checking escalations for team {team.display_name}: {e}")

        except Exception as e:
            logger.exception(f"Error in check_auto_escalations: {e}")
