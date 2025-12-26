"""Admin API endpoints - organized by domain"""
from fastapi import APIRouter

# Import all endpoint routers
from app.routes.admin.endpoints.users import router as users_router
from app.routes.admin.endpoints.teams import router as teams_router
from app.routes.admin.endpoints.schedules import router as schedules_router
from app.routes.admin.endpoints.schedules import shifts_router
from app.routes.admin.endpoints.escalations import router as escalations_router
from app.routes.admin.endpoints.stats import router as stats_router
from app.routes.admin.endpoints.stats import schedules_router as schedules_range_router
from app.routes.admin.endpoints.google_calendar import router as google_calendar_router

# Create main router
router = APIRouter(prefix="/api/admin")

# Register all endpoint routers
router.include_router(users_router)
router.include_router(teams_router)
router.include_router(schedules_router)
router.include_router(shifts_router)
router.include_router(escalations_router)
router.include_router(stats_router)
router.include_router(schedules_range_router)
router.include_router(google_calendar_router)
