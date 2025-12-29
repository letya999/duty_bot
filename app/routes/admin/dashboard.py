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


async def get_session_from_cookie(request: Request):
    """Extract and validate session from cookies"""
    token = request.cookies.get('session_token')
    if not token:
        logger.warning("Dashboard access attempted without session token")
        raise HTTPException(status_code=401, detail="Not authenticated")

    session = await session_manager.validate_session(token)
    if not session:
        logger.warning(f"Invalid or expired session token: {token[:20]}...")
        raise HTTPException(status_code=401, detail="Invalid or expired session")

    logger.debug(f"Valid session found: user_id={session['user_id']}, workspace_id={session['workspace_id']}")
    return session


@router.get("")
async def dashboard_page(request: Request, session: dict = Depends(get_session_from_cookie)):
    """Main dashboard page - Redirect to modern React dashboard"""
    return RedirectResponse(url="/")
