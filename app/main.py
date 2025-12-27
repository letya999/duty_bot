import asyncio
import logging
import os
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
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
from app.routes.miniapp import router as miniapp_router
from app.routes.admin.auth import router as auth_router
from app.routes.admin.dashboard import router as dashboard_router
from app.routes.admin.schedules import router as schedules_router
from app.routes.admin.settings import router as settings_router
from app.routes.admin.reports import router as reports_router, api_router as reports_api_router
from app.routes.admin.api import router as web_api_router
from app.routes.admin.incidents import router as incidents_router
from app.exceptions import (
    ApplicationException,
    ValidationError,
    AuthenticationError,
    AuthorizationError,
    NotFoundError,
    ConflictError,
    CommandError,
)

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
            telegram_chat_id=settings.telegram_chat_id,
            slack_channel_id=settings.slack_channel_id
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


# Create FastAPI app with custom OpenAPI configuration
from app.config import get_openapi_schema

app = FastAPI(
    title="Duty Bot",
    description="API для управления дежурствами",
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/api/docs",
    openapi_url="/api/openapi.json",
    redoc_url="/api/redoc"
)


# ============================================================================
# Exception Handlers
# ============================================================================


async def application_exception_handler(request: Request, exc: ApplicationException):
    """Handle custom application exceptions with structured response"""
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error_code": exc.error_code,
            "message": exc.message,
            "status_code": exc.status_code,
            "details": exc.details if exc.details else None,
        },
    )


async def validation_error_handler(request: Request, exc: ValidationError):
    """Handle validation errors"""
    return await application_exception_handler(request, exc)


async def authentication_error_handler(request: Request, exc: AuthenticationError):
    """Handle authentication errors"""
    return await application_exception_handler(request, exc)


async def authorization_error_handler(request: Request, exc: AuthorizationError):
    """Handle authorization errors"""
    return await application_exception_handler(request, exc)


async def not_found_error_handler(request: Request, exc: NotFoundError):
    """Handle not found errors"""
    return await application_exception_handler(request, exc)


async def conflict_error_handler(request: Request, exc: ConflictError):
    """Handle conflict errors"""
    return await application_exception_handler(request, exc)


async def command_error_handler(request: Request, exc: CommandError):
    """Handle command errors"""
    return await application_exception_handler(request, exc)


# Register exception handlers
app.add_exception_handler(ValidationError, validation_error_handler)
app.add_exception_handler(AuthenticationError, authentication_error_handler)
app.add_exception_handler(AuthorizationError, authorization_error_handler)
app.add_exception_handler(NotFoundError, not_found_error_handler)
app.add_exception_handler(ConflictError, conflict_error_handler)
app.add_exception_handler(CommandError, command_error_handler)
app.add_exception_handler(ApplicationException, application_exception_handler)


# Add CORS middleware for web panel API
# SECURITY: Configurable CORS origins. Use specific origins in production.
# Set CORS_ORIGINS environment variable with comma-separated list of allowed origins
cors_origins_env = os.environ.get('CORS_ORIGINS', '').strip()
if cors_origins_env:
    # Production: use specific allowed origins
    # Strip any trailing slashes from the origins to ensure matching works correctly
    allowed_origins = []
    for origin in cors_origins_env.split(','):
        clean_origin = origin.strip()
        if clean_origin:
            allowed_origins.append(clean_origin)
            # Add version without trailing slash if it has one
            if clean_origin.endswith('/'):
                allowed_origins.append(clean_origin.rstrip('/'))
            # Also add version WITH trailing slash if it doesn't have one (for completeness)
            else:
                allowed_origins.append(f"{clean_origin}/")
    
    allow_credentials = True
    logger.info(f"CORS enabled for specific origins: {list(set(allowed_origins))}")
else:
    # Development fallback: allow all origins but disable credentials for security
    allowed_origins = ["*"]
    allow_credentials = False
    logger.warning("CORS configured for all origins with credentials disabled. Set CORS_ORIGINS for production.")

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=allow_credentials,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Add request logging middleware
@app.middleware("http")
async def log_requests(request: Request, call_next):
    """Log all incoming requests and responses"""
    logger.info(
        f"🔵 [{request.method}] {request.url.path} | "
        f"Origin: {request.headers.get('origin', 'N/A')} | "
        f"Content-Type: {request.headers.get('content-type', 'N/A')}"
    )

    try:
        response = await call_next(request)
        logger.info(
            f"✅ [{request.method}] {request.url.path} | "
            f"Status: {response.status_code}"
        )
        return response
    except Exception as e:
        logger.error(
            f"❌ [{request.method}] {request.url.path} | "
            f"Error: {str(e)}"
        )
        raise


# Register mini app router
app.include_router(miniapp_router)

# Register web panel routers
app.include_router(auth_router)
app.include_router(dashboard_router)
app.include_router(schedules_router)
app.include_router(settings_router)
app.include_router(reports_router)
app.include_router(reports_api_router)
app.include_router(web_api_router)
app.include_router(incidents_router)

# Register authentication API router
from app.routes.admin.auth_api import router as auth_api_router
app.include_router(auth_api_router)


# Custom OpenAPI schema
@app.get("/api/openapi.json", include_in_schema=False)
async def custom_openapi():
    """Serve custom OpenAPI schema"""
    return get_openapi_schema()





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


# Test endpoints for manual task triggering
@app.post("/test/morning-digest")
async def test_morning_digest():
    """Manually trigger morning digest"""
    if not scheduled_tasks:
        return {"error": "Scheduled tasks not initialized"}

    try:
        await scheduled_tasks.morning_digest()
        return {"status": "success", "message": "Morning digest triggered"}
    except Exception as e:
        logger.exception(f"Error triggering morning digest: {e}")
        return {"error": str(e), "status": "failed"}


@app.post("/test/check-escalations")
async def test_check_escalations():
    """Manually trigger escalation check"""
    if not scheduled_tasks:
        return {"error": "Scheduled tasks not initialized"}

    try:
        await scheduled_tasks.check_auto_escalations()
        return {"status": "success", "message": "Escalation check triggered"}
    except Exception as e:
        logger.exception(f"Error triggering escalation check: {e}")
        return {"error": str(e), "status": "failed"}


@app.post("/test/sync-google-calendars")
async def test_sync_google_calendars():
    """Manually trigger Google Calendar sync"""
    if not scheduled_tasks:
        return {"error": "Scheduled tasks not initialized"}

    try:
        await scheduled_tasks.sync_google_calendars()
        return {"status": "success", "message": "Google Calendar sync triggered"}
    except Exception as e:
        logger.exception(f"Error triggering Google Calendar sync: {e}")
        return {"error": str(e), "status": "failed"}


@app.get("/test/scheduler-status")
async def test_scheduler_status():
    """Get scheduler status"""
    if not scheduled_tasks:
        return {"error": "Scheduled tasks not initialized"}

    try:
        jobs = scheduled_tasks.scheduler.get_jobs()
        job_list = []
        for job in jobs:
            job_list.append({
                "id": job.id,
                "name": job.name,
                "next_run_time": str(job.next_run_time),
                "trigger": str(job.trigger)
            })

        return {
            "status": "ok",
            "scheduler_running": scheduled_tasks.scheduler.running,
            "jobs_count": len(job_list),
            "jobs": job_list
        }
    except Exception as e:
        logger.exception(f"Error getting scheduler status: {e}")
        return {"error": str(e), "status": "failed"}



# Serve React static files in production
# Check if React build exists (production deployment)
webapp_dist_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'webapp', 'dist')
if os.path.isdir(webapp_dist_path):
    logger.info(f"Serving React app from {webapp_dist_path}")
    app.mount("/", StaticFiles(directory=webapp_dist_path, html=True), name="static")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "app.main:app",
        host=settings.host,
        port=settings.port,
        reload=False
    )
