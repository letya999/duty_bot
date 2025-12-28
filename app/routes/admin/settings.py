"""Settings and configuration routes for web admin panel"""
import logging
from fastapi import APIRouter, Request, HTTPException, Depends, Form
from fastapi.responses import HTMLResponse, RedirectResponse
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
    """Settings page - Redirect to modern React dashboard"""
    return RedirectResponse(url="/settings")
