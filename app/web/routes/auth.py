"""Authentication routes for web panel"""
import logging
from fastapi import APIRouter, Request, Response, HTTPException, Depends
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
import secrets
from urllib.parse import urlencode

from app.config import get_settings
from app.web.auth import (
    TelegramOAuth, SlackOAuth, session_manager, get_or_create_user
)

logger = logging.getLogger(__name__)
settings = get_settings()

router = APIRouter(prefix="/web/auth", tags=["web-auth"])

# OAuth providers
telegram_oauth = TelegramOAuth()
slack_oauth = SlackOAuth()

# Store pending states for CSRF protection
pending_states = {}


def get_session_from_cookie(request: Request) -> dict:
    """Extract session from cookies"""
    token = request.cookies.get('session_token')
    if not token:
        raise HTTPException(status_code=401, detail="Not authenticated")

    session = session_manager.validate_session(token)
    if not session:
        raise HTTPException(status_code=401, detail="Invalid or expired session")

    return session


@router.get("/login")
async def login_page(request: Request):
    """Login page with provider options"""
    html = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Duty Bot - Admin Panel Login</title>
        <meta charset="utf-8">
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <style>
            * { margin: 0; padding: 0; box-sizing: border-box; }
            body {
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                min-height: 100vh;
                display: flex;
                align-items: center;
                justify-content: center;
            }
            .login-container {
                background: white;
                border-radius: 10px;
                box-shadow: 0 10px 40px rgba(0, 0, 0, 0.2);
                padding: 40px;
                max-width: 400px;
                width: 100%;
            }
            h1 {
                text-align: center;
                margin-bottom: 10px;
                color: #333;
            }
            .subtitle {
                text-align: center;
                color: #666;
                margin-bottom: 30px;
                font-size: 14px;
            }
            .login-options {
                display: flex;
                flex-direction: column;
                gap: 15px;
            }
            .login-btn {
                padding: 12px 20px;
                border: none;
                border-radius: 5px;
                font-size: 16px;
                cursor: pointer;
                display: flex;
                align-items: center;
                justify-content: center;
                gap: 10px;
                text-decoration: none;
                transition: opacity 0.3s;
            }
            .login-btn:hover {
                opacity: 0.9;
            }
            .telegram-btn {
                background: #0088cc;
                color: white;
            }
            .slack-btn {
                background: #36c5f0;
                color: white;
            }
        </style>
    </head>
    <body>
        <div class="login-container">
            <h1>Duty Bot</h1>
            <p class="subtitle">Admin Panel</p>
            <div class="login-options">
                <a href="/web/auth/telegram-login" class="login-btn telegram-btn">
                    ✈️ Login with Telegram
                </a>
                <a href="/web/auth/slack-login" class="login-btn slack-btn">
                    ⚡ Login with Slack
                </a>
            </div>
        </div>
    </body>
    </html>
    """
    return HTMLResponse(content=html)


@router.get("/telegram-login")
async def telegram_login(request: Request):
    """Telegram login redirect"""
    # In production, would use TG Login Widget or manual validation
    # For now, show info about manual validation
    html = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Telegram Login</title>
        <script async src="https://telegram.org/js/telegram-web-app.js"></script>
        <style>
            body {
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                padding: 20px;
                background: #f5f5f5;
            }
            .container {
                max-width: 500px;
                margin: 0 auto;
                background: white;
                padding: 20px;
                border-radius: 10px;
            }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>Telegram Login</h1>
            <p>Opening Telegram login...</p>
            <p id="status">Loading...</p>
        </div>
        <script>
            const tg = window.Telegram.WebApp;

            async function authenticate() {
                const initData = tg.initData;
                if (!initData) {
                    document.getElementById('status').textContent = 'Error: initData not available';
                    return;
                }

                try {
                    const response = await fetch('/web/auth/telegram-callback', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
                        body: 'init_data=' + encodeURIComponent(initData)
                    });

                    if (response.ok) {
                        window.location.href = '/web/dashboard';
                    } else {
                        const data = await response.json();
                        document.getElementById('status').textContent = 'Error: ' + data.detail;
                    }
                } catch (error) {
                    document.getElementById('status').textContent = 'Error: ' + error.message;
                }
            }

            authenticate();
        </script>
    </body>
    </html>
    """
    return HTMLResponse(content=html)


@router.post("/telegram-callback")
async def telegram_callback(request: Request):
    """Handle Telegram OAuth callback"""
    try:
        form_data = await request.form()
        init_data = form_data.get('init_data')

        if not init_data:
            raise HTTPException(status_code=400, detail="No init data provided")

        # Validate Telegram init data
        user_info = await telegram_oauth.validate_init_data(init_data)
        if not user_info:
            raise HTTPException(status_code=401, detail="Invalid Telegram authentication")

        # Get or create user
        user = await get_or_create_user('telegram', user_info)
        if not user:
            raise HTTPException(status_code=500, detail="Failed to create user")

        # Get user's workspace (first workspace by default)
        from app.database import AsyncSessionLocal
        from sqlalchemy import select
        async with AsyncSessionLocal() as db:
            # Get workspaces for this user
            stmt = select(Workspace).limit(1)
            result = await db.execute(stmt)
            workspace = result.scalars().first()

            if not workspace:
                # Create default workspace if needed
                from app.models import Workspace as WorkspaceModel
                workspace = WorkspaceModel(
                    platform='telegram',
                    platform_id=str(user_info['user_id']),
                    name=f"Workspace for {user_info.get('first_name', 'User')}"
                )
                db.add(workspace)
                await db.commit()

        # Create session
        session_token = session_manager.create_session(
            user.id,
            workspace.id,
            'telegram'
        )

        response = RedirectResponse(url="/web/dashboard", status_code=302)
        response.set_cookie(
            "session_token",
            session_token,
            max_age=86400,
            httponly=True,
            samesite="Lax"
        )
        return response

    except Exception as e:
        logger.error(f"Error in Telegram callback: {e}")
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/slack-login")
async def slack_login(request: Request):
    """Slack login redirect"""
    state = secrets.token_urlsafe(32)
    pending_states[state] = {
        'created_at': None,  # Will be set to datetime.now()
    }

    auth_url = await slack_oauth.get_auth_url(state)
    return RedirectResponse(url=auth_url)


@router.get("/slack-callback")
async def slack_callback(code: str = None, state: str = None):
    """Handle Slack OAuth callback"""
    try:
        if not code or not state:
            raise HTTPException(status_code=400, detail="Missing code or state")

        if state not in pending_states:
            raise HTTPException(status_code=400, detail="Invalid state")

        # Exchange code for token
        token_info = await slack_oauth.exchange_code_for_token(code)
        if not token_info:
            raise HTTPException(status_code=401, detail="Failed to get access token")

        # Get user info
        user_info = await slack_oauth.get_user_info(token_info['access_token'])
        if not user_info:
            raise HTTPException(status_code=401, detail="Failed to get user info")

        # Get or create user
        user = await get_or_create_user('slack', user_info)
        if not user:
            raise HTTPException(status_code=500, detail="Failed to create user")

        # Get or create workspace
        from app.database import AsyncSessionLocal
        from sqlalchemy import select
        from app.models import Workspace

        async with AsyncSessionLocal() as db:
            stmt = select(Workspace).where(
                Workspace.platform_id == token_info['team_id']
            )
            result = await db.execute(stmt)
            workspace = result.scalars().first()

            if not workspace:
                workspace = Workspace(
                    platform='slack',
                    platform_id=token_info['team_id'],
                    name=token_info['team_name']
                )
                db.add(workspace)
                await db.commit()

        # Create session
        session_token = session_manager.create_session(
            user.id,
            workspace.id,
            'slack'
        )

        response = RedirectResponse(url="/web/dashboard", status_code=302)
        response.set_cookie(
            "session_token",
            session_token,
            max_age=86400,
            httponly=True,
            samesite="Lax"
        )

        # Clean up state
        del pending_states[state]

        return response

    except Exception as e:
        logger.error(f"Error in Slack callback: {e}")
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/logout")
async def logout(request: Request):
    """Logout user"""
    token = request.cookies.get('session_token')
    if token:
        session_manager.revoke_session(token)

    response = RedirectResponse(url="/web/auth/login", status_code=302)
    response.delete_cookie("session_token")
    return response
