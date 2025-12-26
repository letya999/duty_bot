"""Authentication routes for web panel"""
import logging
import os
from fastapi import APIRouter, Request, Response, HTTPException, Depends
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
import secrets
from urllib.parse import urlencode
from sqlalchemy import select

from app.config import get_settings
from app.auth import (
    TelegramOAuth, SlackOAuth, session_manager
)
from app.models import Workspace, User
from app.database import AsyncSessionLocal

logger = logging.getLogger(__name__)
settings = get_settings()

router = APIRouter(prefix="/web/auth", tags=["web-auth"])

# OAuth providers
telegram_oauth = TelegramOAuth()
slack_oauth = SlackOAuth()

# Store pending states for CSRF protection
pending_states = {}


def get_session_from_cookie(request: Request) -> dict:
    """Extract session from cookies or Authorization header"""
    token = request.cookies.get('session_token')
    
    # Also check Authorization header for flexibility
    if not token:
        auth_header = request.headers.get("Authorization")
        if auth_header and auth_header.startswith("Bearer "):
            token = auth_header.split(" ", 1)[1]
            
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
                        credentials: 'include',
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
            logger.error("No init data provided in request")
            raise HTTPException(status_code=400, detail="No init data provided")

        # Validate Telegram init data
        user_info = await telegram_oauth.validate_init_data(init_data)
        if not user_info:
            logger.error(f"Failed to validate Telegram init data: {init_data[:50]}")
            raise HTTPException(status_code=401, detail="Invalid Telegram authentication")

        logger.info(f"Validated Telegram user: {user_info}")

        # Get or create user and workspace
        async with AsyncSessionLocal() as db:
            # 1. Try to find an existing user record with this telegram_id
            user_stmt = select(User).where(User.telegram_id == user_info['user_id']).order_by(User.is_admin.desc())
            result = await db.execute(user_stmt)
            existing_user = result.scalars().first()

            if existing_user:
                logger.info(f"Found existing user {existing_user.id} in workspace {existing_user.workspace_id}")
                user = existing_user
                workspace = await db.get(Workspace, user.workspace_id)
            else:
                # 2. If no user found, look for or create a personal workspace
                workspace_stmt = select(Workspace).where(
                    (Workspace.workspace_type == 'telegram') &
                    (Workspace.external_id == str(user_info['user_id']))
                )
                result = await db.execute(workspace_stmt)
                workspace = result.scalars().first()

                if not workspace:
                    logger.info(f"Creating new workspace for Telegram user {user_info['user_id']}")
                    workspace = Workspace(
                        workspace_type='telegram',
                        external_id=str(user_info['user_id']),
                        name=f"Workspace for {user_info.get('first_name', 'User')}"
                    )
                    db.add(workspace)
                    await db.commit()
                    await db.refresh(workspace)
                    logger.info(f"Created workspace: {workspace.id}")
                else:
                    logger.info(f"Found existing workspace: {workspace.id}")

                user = None # Will be created below

            # Get or create user with workspace_id set
            # First try to find by telegram_id
            user_stmt = select(User).where(
                (User.telegram_id == user_info['user_id']) &
                (User.workspace_id == workspace.id)
            )
            result = await db.execute(user_stmt)
            user = result.scalars().first()

            # If not found by ID, try to find by username (for backwards compatibility)
            if not user and user_info.get('username'):
                logger.info(f"User not found by telegram_id, trying by username: {user_info.get('username')}")
                user_stmt = select(User).where(
                    (User.telegram_username == user_info.get('username')) &
                    (User.workspace_id == workspace.id)
                )
                result = await db.execute(user_stmt)
                user = result.scalars().first()

                if user:
                    logger.info(f"Found existing user by username: {user.id}, updating telegram_id")
                    user.telegram_id = user_info['user_id']
                    await db.commit()
                    await db.refresh(user)

            if not user:
                logger.info(f"Creating new user for Telegram ID {user_info['user_id']}")
                first_name = user_info.get('first_name')
                last_name = user_info.get('last_name')
                username = user_info.get('username')
                
                user = User(
                    workspace_id=workspace.id,
                    telegram_id=user_info['user_id'],
                    telegram_username=username,
                    username=username or str(user_info['user_id']),
                    first_name=first_name,
                    last_name=last_name,
                    display_name=f"{first_name or ''} {last_name or ''}".strip() or username or str(user_info['user_id'])
                )
                db.add(user)
                await db.commit()
                await db.refresh(user)
                logger.info(f"Created user: {user.id}")
            else:
                logger.info(f"Found existing user: {user.id}")

        # Create session
        session_token = session_manager.create_session(
            user.id,
            workspace.id,
            'telegram'
        )
        logger.info(f"Created session token for user {user.id}")

        response = RedirectResponse(url="/web/dashboard", status_code=302)
        # Determine if we're in production (use HTTPS)
        is_production = os.environ.get('ENVIRONMENT', 'development').lower() == 'production'
        response.set_cookie(
            "session_token",
            session_token,
            max_age=86400,
            httponly=True,
            samesite="Lax",
            secure=is_production  # Only set secure flag in production with HTTPS
        )
        logger.info(f"Setting session cookie and redirecting to dashboard")
        return response

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in Telegram callback: {e}", exc_info=True)
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/telegram-widget-callback")
async def telegram_widget_callback(request: Request):
    """Handle Telegram Login Widget callback (for web admin panel)"""
    try:
        logger.info("🔵 [Backend] POST /telegram-widget-callback received")
        logger.info(f"🔵 [Backend] Request headers: {dict(request.headers)}")

        data = await request.json()
        logger.info(f"🔵 [Backend] JSON body parsed successfully")
        logger.info(f"🔵 [Backend] Data keys: {list(data.keys())}")
        logger.info(f"🔵 [Backend] Data: {data}")

        if not data.get('id'):
            logger.error("❌ [Backend] No user ID provided in widget callback")
            raise HTTPException(status_code=400, detail="No user ID provided")

        logger.info(f"🔵 [Backend] User ID present: {data.get('id')}")

        # Validate the widget data
        logger.info(f"🔵 [Backend] Validating widget data...")
        user_info = await telegram_oauth.validate_widget_data(data)
        if not user_info:
            logger.error(f"❌ [Backend] Failed to validate widget data")
            raise HTTPException(status_code=401, detail="Invalid Telegram authentication")

        logger.info(f"✅ [Backend] Validation SUCCESS: {user_info}")

        # Get or create user and workspace
        # Get user
        async with AsyncSessionLocal() as db:
            # 1. Try to find an existing user record with this telegram_id
            # Order by is_admin desc to prefer workspaces where the user is an admin
            # Order by created_at desc to prefer more recently created/active profiles as a tie-breaker
            user_stmt = select(User).where(User.telegram_id == user_info['user_id']).order_by(User.is_admin.desc(), User.created_at.desc())
            result = await db.execute(user_stmt)
            existing_user = result.scalars().first()

            if existing_user:
                logger.info(f"Found existing user {existing_user.id} in workspace {existing_user.workspace_id}")
                
                # Verify if user is admin in THIS workspace or a master admin
                # Since we ordered by is_admin desc, if the first result is not admin, they aren't admin anywhere
                is_admin = existing_user.is_admin
                from app.config import get_settings
                settings = get_settings()
                if existing_user.telegram_id and str(existing_user.telegram_id) in settings.get_admin_ids('telegram'):
                    is_admin = True
                
                if not is_admin:
                    logger.warning(f"User {user_info['user_id']} found but is not an admin in any workspace.")
                    raise HTTPException(status_code=403, detail="Access denied. Only administrators can access the web panel.")
                
                user = existing_user
                workspace = await db.get(Workspace, user.workspace_id)
            else:
                # Per user request: DO NOT CREATE NEW USERS/WORKSPACES via login
                logger.warning(f"User {user_info['user_id']} not found in any workspace and registration is disabled.")
                raise HTTPException(status_code=403, detail="User not found. Please ask your administrator to add you to a team first.")

        # Create session
        session_token = session_manager.create_session(
            user.id,
            workspace.id,
            'telegram'
        )
        logger.info(f"✅ [Backend] Created session token for user {user.id}")

        from fastapi.responses import JSONResponse
        response = JSONResponse(content={
            "success": True,
            "session_token": session_token,
            "user": {
                "id": user.id,
                "telegram_username": user.telegram_username,
                "first_name": user.first_name,
                "last_name": user.last_name,
                "is_admin": user.is_admin,
                "workspace_id": user.workspace_id,
            }
        })
        
        # Set cookie for web panel
        response.set_cookie(
            "session_token",
            session_token,
            max_age=86400,
            httponly=True,
            samesite="Lax",
            secure=True # ngrok uses https
        )
        
        logger.info(f"✅ [Backend] Returning success response and setting cookie")
        return response

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ [Backend] Error in Telegram widget callback: {e}", exc_info=True)
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
            logger.error("Missing code or state in Slack callback")
            raise HTTPException(status_code=400, detail="Missing code or state")

        if state not in pending_states:
            logger.error(f"Invalid state in Slack callback: {state}")
            raise HTTPException(status_code=400, detail="Invalid state")

        # Exchange code for token
        token_info = await slack_oauth.exchange_code_for_token(code)
        if not token_info:
            logger.error("Failed to exchange Slack code for token")
            raise HTTPException(status_code=401, detail="Failed to get access token")

        # Get user info
        user_info = await slack_oauth.get_user_info(token_info['access_token'])
        if not user_info:
            logger.error("Failed to get Slack user info")
            raise HTTPException(status_code=401, detail="Failed to get user info")

        logger.info(f"Validated Slack user: {user_info}")

        # Get or create user and workspace
        async with AsyncSessionLocal() as db:
            # Get or create workspace for this Slack team
            workspace_stmt = select(Workspace).where(
                (Workspace.workspace_type == 'slack') &
                (Workspace.external_id == token_info['team_id'])
            )
            result = await db.execute(workspace_stmt)
            workspace = result.scalars().first()

            if not workspace:
                logger.info(f"Creating new workspace for Slack team {token_info['team_id']}")
                # Create workspace for this Slack team
                workspace = Workspace(
                    workspace_type='slack',
                    external_id=token_info['team_id'],
                    name=token_info['team_name']
                )
                db.add(workspace)
                await db.commit()
                await db.refresh(workspace)
                logger.info(f"Created workspace: {workspace.id}")
            else:
                logger.info(f"Found existing workspace: {workspace.id}")

            # Get or create user with workspace_id set
            # First try to find by slack_user_id
            user_stmt = select(User).where(
                (User.slack_user_id == user_info['user_id']) &
                (User.workspace_id == workspace.id)
            )
            result = await db.execute(user_stmt)
            user = result.scalars().first()

            # If not found by slack_user_id, try to find by username (for backwards compatibility)
            if not user and user_info.get('username'):
                logger.info(f"User not found by slack_user_id, trying by username: {user_info.get('username')}")
                user_stmt = select(User).where(
                    (User.username == user_info.get('username')) &
                    (User.workspace_id == workspace.id)
                )
                result = await db.execute(user_stmt)
                user = result.scalars().first()

                if user:
                    logger.info(f"Found existing user by username: {user.id}, updating slack_user_id")
                    user.slack_user_id = user_info['user_id']
                    await db.commit()
                    await db.refresh(user)

            if not user:
                logger.info(f"Creating new user for Slack user ID {user_info['user_id']}")
                username = user_info.get('username')
                real_name = user_info.get('real_name')
                
                user = User(
                    workspace_id=workspace.id,
                    slack_user_id=user_info['user_id'],
                    username=username,
                    display_name=real_name or username or user_info['user_id']
                )
                db.add(user)
                await db.commit()
                await db.refresh(user)
                logger.info(f"Created user: {user.id}")
            else:
                logger.info(f"Found existing user: {user.id}")

        # Create session
        session_token = session_manager.create_session(
            user.id,
            workspace.id,
            'slack'
        )
        logger.info(f"Created session token for user {user.id}")

        response = RedirectResponse(url="/web/dashboard", status_code=302)
        # Determine if we're in production (use HTTPS)
        is_production = os.environ.get('ENVIRONMENT', 'development').lower() == 'production'
        response.set_cookie(
            "session_token",
            session_token,
            max_age=86400,
            httponly=True,
            samesite="Lax",
            secure=is_production  # Only set secure flag in production with HTTPS
        )
        logger.info(f"Setting session cookie and redirecting to dashboard")

        # Clean up state
        del pending_states[state]

        return response

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in Slack callback: {e}", exc_info=True)
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


@router.get("/workspaces")
async def list_workspaces(request: Request, session: dict = Depends(get_session_from_cookie)):
    """Get list of available workspaces for current user.

    Returns workspaces where the user has access (is a member or admin).
    If user is only in one workspace, return that single workspace.
    """
    try:
        user_id = session['user_id']
        current_workspace_id = session['workspace_id']

        async with AsyncSessionLocal() as db:
            # Get current user to access their telegram_id or slack_user_id
            current_user = await db.get(User, user_id)
            if not current_user:
                raise HTTPException(status_code=404, detail="User not found")

            # Find all workspaces where this user exists with same platform ID
            # This ensures we only list workspaces where the user actually belongs
            stmt = select(User).where(
                User.telegram_id == current_user.telegram_id if current_user.telegram_id else None or
                User.slack_user_id == current_user.slack_user_id if current_user.slack_user_id else None
            )

            if current_user.telegram_id:
                stmt = select(User).where(User.telegram_id == current_user.telegram_id)
            elif current_user.slack_user_id:
                stmt = select(User).where(User.slack_user_id == current_user.slack_user_id)
            else:
                raise HTTPException(status_code=400, detail="User has no platform ID")

            result = await db.execute(stmt)
            all_user_records = result.scalars().all()

            # Build workspace list from all user records
            workspaces = []
            workspace_ids = set()

            admin_telegram_ids = settings.get_admin_ids('telegram')
            admin_slack_ids = settings.get_admin_ids('slack')

            for user_record in all_user_records:
                if user_record.workspace_id not in workspace_ids:
                    workspace_ids.add(user_record.workspace_id)
                    workspace = await db.get(Workspace, user_record.workspace_id)
                    if workspace:
                        is_admin = user_record.is_admin
                        
                        # Master admin bypass
                        if user_record.telegram_id and str(user_record.telegram_id) in admin_telegram_ids:
                            is_admin = True
                        if user_record.slack_user_id and user_record.slack_user_id in admin_slack_ids:
                            is_admin = True

                        # Filter: only show if admin or master admin
                        if is_admin:
                            workspaces.append({
                                'id': workspace.id,
                                'name': workspace.name,
                                'type': workspace.workspace_type,
                                'is_current': workspace.id == current_workspace_id,
                                'is_admin': is_admin,
                                'role': 'admin' if is_admin else 'member'
                            })

            logger.info(f"User {user_id} has access to {len(workspaces)} workspace(s)")
            return {'workspaces': workspaces}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error listing workspaces: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to list workspaces")


@router.post("/switch-workspace")
async def switch_workspace(request: Request, session: dict = Depends(get_session_from_cookie)):
    """Switch to a different workspace.

    Request body: {"workspace_id": <id>}
    Response: New session token
    """
    try:
        user_id = session['user_id']
        current_workspace_id = session['workspace_id']

        data = await request.json()
        target_workspace_id = data.get('workspace_id')

        if not target_workspace_id:
            raise HTTPException(status_code=400, detail="Missing workspace_id")

        if target_workspace_id == current_workspace_id:
            logger.info(f"User {user_id} already in workspace {target_workspace_id}")
            return {
                'session_token': request.cookies.get('session_token'),
                'message': 'Already in this workspace'
            }

        async with AsyncSessionLocal() as db:
            # Get current user to get their platform ID
            current_user = await db.get(User, user_id)
            if not current_user:
                raise HTTPException(status_code=404, detail="User not found")

            # Find user record in target workspace with same platform ID
            if current_user.telegram_id:
                target_user_stmt = select(User).where(
                    User.telegram_id == current_user.telegram_id,
                    User.workspace_id == target_workspace_id
                )
            elif current_user.slack_user_id:
                target_user_stmt = select(User).where(
                    User.slack_user_id == current_user.slack_user_id,
                    User.workspace_id == target_workspace_id
                )
            else:
                raise HTTPException(status_code=400, detail="User has no platform ID")

            result = await db.execute(target_user_stmt)
            target_user = result.scalar_one_or_none()

            if not target_user:
                logger.warning(f"User {user_id} not found in target workspace {target_workspace_id}")
                raise HTTPException(status_code=403, detail="Access denied to this workspace")

            # Verify admin status for the target workspace
            from app.config import get_settings
            settings = get_settings()
            is_admin = target_user.is_admin
            
            # Master admin bypass
            if target_user.telegram_id and str(target_user.telegram_id) in settings.get_admin_ids('telegram'):
                is_admin = True
            if target_user.slack_user_id and target_user.slack_user_id in settings.get_admin_ids('slack'):
                is_admin = True

            if not is_admin:
                logger.warning(f"User {user_id} attempted to switch to workspace {target_workspace_id} without admin rights")
                raise HTTPException(status_code=403, detail="You do not have administrator permissions in this workspace")

            # Verify workspace exists
            target_workspace = await db.get(Workspace, target_workspace_id)
            if not target_workspace:
                raise HTTPException(status_code=404, detail="Workspace not found")

            logger.info(f"Switching user {user_id} from workspace {current_workspace_id} to {target_workspace_id}")

        # Create new session for target workspace
        new_token = session_manager.create_session(
            target_user.id,
            target_workspace_id,
            target_workspace.workspace_type
        )

        from fastapi.responses import JSONResponse
        response = JSONResponse(content={
            'success': True,
            'session_token': new_token,
            'workspace': {
                'id': target_workspace_id,
                'name': target_workspace.name,
                'type': target_workspace.workspace_type
            }
        })
        
        response.set_cookie(
            "session_token",
            new_token,
            max_age=86400,
            httponly=True,
            samesite="Lax",
            secure=True
        )
        
        return response

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error switching workspace: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to switch workspace")
