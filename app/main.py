import asyncio
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from slack_bolt.async_app import AsyncApp
from slack_bolt.adapter.fastapi.async_handler import AsyncSlackRequestHandler
from telegram import Bot
try:
    from slack_sdk.web.async_client import AsyncWebClient
except ImportError:
    from slack_sdk.web import AsyncWebClient
from app.config import get_settings
from app.database import init_db, close_db, AsyncSessionLocal
from app.handlers.telegram_handler import TelegramHandler
from app.handlers.slack_handler import SlackHandler
from app.tasks.scheduled_tasks import ScheduledTasks

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

settings = get_settings()

# Global instances
telegram_handler = None
slack_handler = None
scheduled_tasks = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan context manager for FastAPI"""
    # Startup
    try:
        logger.info("Starting Duty Bot...")

        # Initialize database
        await init_db()
        logger.info("Database initialized")

        # Setup Telegram
        global telegram_handler
        if settings.telegram_token:
            telegram_handler = TelegramHandler()
            await telegram_handler.start()
            logger.info("Telegram bot started")
        else:
            logger.warning("Telegram token not provided, Telegram bot will not start")

        # Setup Slack
        global slack_handler
        if settings.slack_bot_token and settings.slack_signing_secret:
            slack_handler = SlackHandler()
            logger.info("Slack bot started")
        else:
            logger.warning("Slack tokens not provided, Slack bot will not start")

        # Setup scheduled tasks
        global scheduled_tasks
        slack_client = None
        if settings.slack_bot_token:
            slack_client = AsyncWebClient(token=settings.slack_bot_token)
        
        telegram_bot = None
        if settings.telegram_token:
            telegram_bot = Bot(token=settings.telegram_token)

        scheduled_tasks = ScheduledTasks(
            telegram_bot=telegram_bot,
            slack_client=slack_client,
            telegram_chat_id=None,  # Will be set from environment or config
            slack_channel_id=None   # Will be set from environment or config
        )
        await scheduled_tasks.start()
        logger.info("Scheduled tasks started")

        logger.info("Duty Bot started successfully!")

    except Exception as e:
        logger.exception(f"Failed to start bot: {e}")
        raise

    yield

    # Shutdown
    try:
        logger.info("Shutting down Duty Bot...")

        if scheduled_tasks:
            await scheduled_tasks.stop()
            logger.info("Scheduled tasks stopped")

        if telegram_handler:
            await telegram_handler.stop()
            logger.info("Telegram bot stopped")

        await close_db()
        logger.info("Database closed")

        logger.info("Duty Bot stopped")

    except Exception as e:
        logger.exception(f"Error during shutdown: {e}")


# Create FastAPI app
app = FastAPI(title="Duty Bot", lifespan=lifespan)


@app.get("/health")
async def health():
    """Health check endpoint"""
    return {"status": "ok"}


@app.post("/slack/events")
async def slack_events(request: Request):
    """Slack events endpoint"""
    if slack_handler and slack_handler.app:
        handler = AsyncSlackRequestHandler(slack_handler.app)
        return await handler.handle(request)
    return {"error": "Slack handler not initialized"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "app.main:app",
        host=settings.host,
        port=settings.port,
        reload=False
    )
