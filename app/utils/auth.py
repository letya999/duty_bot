"""
Authentication utilities and helpers.
"""

import logging
import os
from typing import Dict, Any, Optional

from fastapi import Request, HTTPException
from fastapi.responses import Response

from app.auth import session_manager

logger = logging.getLogger(__name__)


async def get_session_from_cookie(request: Request) -> Dict[str, Any]:
    """
    Extract and validate session from cookies or Authorization header.

    Checks:
    1. session_token cookie (preferred)
    2. Authorization: Bearer <token> header (fallback)

    Raises:
        HTTPException: 401 if token missing or invalid
    """
    token = request.cookies.get("session_token")

    # Fallback to Authorization header
    if not token:
        auth_header = request.headers.get("Authorization")
        if auth_header and auth_header.startswith("Bearer "):
            temp_token = auth_header.split(" ", 1)[1]
            # Filter out JS null/undefined strings
            if temp_token and temp_token not in ("null", "undefined"):
                token = temp_token

    if not token:
        raise HTTPException(status_code=401, detail="Not authenticated")

    session = await session_manager.validate_session(token)
    if not session:
        raise HTTPException(status_code=401, detail="Invalid or expired session")

    return session


def set_session_cookie(
    response: Response,
    session_token: str,
    secure: Optional[bool] = None,
    samesite: str = "Lax",
) -> None:
    """
    Set session cookie on response.

    Args:
        response: FastAPI response object
        session_token: Session token to set
        secure: Use HTTPS only. If None, auto-detect from environment
        samesite: Cookie SameSite attribute ("Lax", "Strict", or "None")
    """
    if secure is None:
        # Auto-detect from environment
        is_production = os.environ.get("ENVIRONMENT", "development").lower() == "production"
        secure = is_production and samesite != "Lax"

    response.set_cookie(
        "session_token",
        session_token,
        max_age=86400,  # 24 hours
        httponly=True,
        samesite=samesite,
        path="/",
        secure=secure,
    )


def clear_session_cookie(response: Response) -> None:
    """Clear session cookie from response."""
    response.delete_cookie("session_token")


def build_user_data_json(user_data: Dict[str, Any]) -> str:
    """
    Build JSON string for localStorage user data.

    Uses double-encoding to ensure proper escaping in HTML.
    """
    import json

    return json.dumps(json.dumps(user_data))
