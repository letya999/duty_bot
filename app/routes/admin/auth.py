"""Authentication routes for web panel"""
import logging
import os
from fastapi import APIRouter, Request, Response, HTTPException, Depends
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
import json
import secrets
from urllib.parse import urlencode
from sqlalchemy import select

from app.config import get_settings
from app.auth import (
    TelegramOAuth, SlackOAuth, session_manager
)
from app.models import Workspace, User
from app.database import AsyncSessionLocal
from app.middleware.rate_limiter import limiter, get_rate_limit
from app.middleware.csrf_protection import csrf_protection

logger = logging.getLogger(__name__)
settings = get_settings()

router = APIRouter(tags=["web-auth"])

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


@router.get("/web/auth/login")
async def login_page(request: Request):
    """Login page - Redirect to modern React dashboard"""
    return RedirectResponse(url="/")


@router.get("/web/auth/telegram-login")
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


@router.post("/web/auth/telegram-callback")
@limiter.limit(get_rate_limit("auth_strict"))
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
            user_stmt = select(User).where(User.telegram_id == user_info['user_id']).order_by(User.is_superadmin.desc(), User.is_admin.desc())
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

        # Prepare user data for React
        user_data = {
            "id": user.id,
            "username": user.username or user.telegram_username,
            "first_name": user.first_name,
            "last_name": user.last_name,
            "is_admin": user.is_admin,
            "is_superadmin": user.is_superadmin,
            "workspace_id": user.workspace_id,
        }
        
        # Master admin check
        if user.telegram_id and str(user.telegram_id) in settings.get_admin_ids('telegram'):
            user_data["is_admin"] = True
            if not user.is_admin:
                # Update in memory and potentially DB
                user_data["is_admin"] = True
        
        # Superadmin check
        if user.is_superadmin:
            user_data["is_superadmin"] = True

        # Return bridge HTML to set user data and redirect to modern dashboard
        # Security: Session token is stored in httpOnly cookie only (not localStorage)
        # to protect against XSS attacks
        html = f"""
        <!DOCTYPE html>
        <html>
        <head><title>Redirecting...</title></head>
        <body>
            <script>
                // Store only non-sensitive user data for UI state
                localStorage.setItem('user', {json.dumps(json.dumps(user_data))});
                // Session token is in httpOnly cookie - DO NOT store in localStorage
                window.location.href = '/';
            </script>
        </body>
        </html>
        """
        response = HTMLResponse(content=html)
        # Determine if we're in production (use HTTPS)
        is_production = os.environ.get('ENVIRONMENT', 'development').lower() == 'production'
        response.set_cookie(
            "session_token",
            session_token,
            max_age=86400,
            httponly=True,
            samesite="Lax",
            secure=True  # Usually HTTPS via ngrok or prod
        )
        logger.info(f"Setting session cookie and redirection bridge for Telegram user {user.id}")
        return response

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in Telegram callback: {e}", exc_info=True)
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/web/auth/telegram-widget-callback")
@limiter.limit(get_rate_limit("auth_strict"))
async def telegram_widget_callback(
    request: Request,
    user_account_service: "UserAccountService" = Depends(lambda: None) # Will be resolved below if possible or used manually
):
    """Handle Telegram Login Widget callback (for web admin panel)"""
    from app.routes.admin.dependencies import get_user_account_service
    # We might need to resolve it manually since this is a route but let's try Depends first
    # Actually, let's use the manual way to be safe in this complex file
    
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
            user_stmt = select(User).where(User.telegram_id == user_info['user_id']).order_by(User.is_superadmin.desc(), User.is_admin.desc(), User.created_at.desc())
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
                "username": user.username or user.telegram_username,
                "telegram_username": user.telegram_username,
                "first_name": user.first_name,
                "last_name": user.last_name,
                "is_admin": user.is_admin or (user.telegram_id and str(user.telegram_id) in settings.get_admin_ids('telegram')),
                "is_superadmin": user.is_superadmin,
                "workspace_id": user.workspace_id,
            }
        })
        
        # Ensure UserAccount entry exists
        try:
            from app.repositories.user_account_repository import UserAccountRepository
            from app.repositories.user_repository import UserRepository
            from app.services.user_account_service import UserAccountService
            
            async with AsyncSessionLocal() as db:
                ua_service = UserAccountService(UserAccountRepository(db), UserRepository(db), db)
                await ua_service.find_or_create_account(
                    user_id=user.id,
                    provider='telegram',
                    provider_id=str(user_info['user_id']),
                    workspace_id=user.workspace_id,
                    username=user_info.get('username')
                )
        except Exception as e:
            logger.warning(f"Failed to create/update UserAccount during login: {e}")
        
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


@router.get("/web/auth/slack-login")
async def slack_login(request: Request):
    """Slack login redirect"""
    state = secrets.token_urlsafe(32)
    pending_states[state] = {
        'created_at': None,  # Will be set to datetime.now()
    }

    auth_url = await slack_oauth.get_auth_url(state)
    return RedirectResponse(url=auth_url)


@router.get("/api/admin/auth/slack/callback")
@limiter.limit(get_rate_limit("auth_strict"))
async def slack_callback(request: Request, code: str = None, state: str = None):
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

        # Get user info - pass user_id to avoid identifying as bot
        user_info = await slack_oauth.get_user_info(
            token_info['access_token'], 
            token_info.get('user_id')
        )
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
                
                user = User(
                    workspace_id=workspace.id,
                    slack_user_id=user_info['user_id'],
                    username=user_info.get('username'),
                    first_name=user_info.get('first_name'),
                    last_name=user_info.get('last_name'),
                    display_name=user_info.get('display_name') or user_info.get('real_name') or user_info.get('username')
                )
                db.add(user)
                await db.commit()
                await db.refresh(user)
                logger.info(f"Created user: {user.id}")
            else:
                logger.info(f"Found existing user: {user.id}")
                # Update names if missing
                updated = False
                if not user.first_name and user_info.get('first_name'):
                    user.first_name = user_info['first_name']
                    updated = True
                if not user.last_name and user_info.get('last_name'):
                    user.last_name = user_info['last_name']
                    updated = True
                if not user.display_name and user_info.get('display_name'):
                    user.display_name = user_info['display_name']
                    updated = True
                
                if updated:
                    await db.commit()
                    await db.refresh(user)

        # Create session
        session_token = session_manager.create_session(
            user.id,
            workspace.id,
            'slack'
        )
        logger.info(f"Created session token for user {user.id}")

        # Prepare user data for React
        user_data = {
            "id": user.id,
            "username": user.username,
            "first_name": user.first_name,
            "last_name": user.last_name,
            "is_admin": user.is_admin,
            "is_superadmin": user.is_superadmin,
            "workspace_id": user.workspace_id,
        }
        
        # Master admin check
        is_admin = user.is_admin
        if user.slack_user_id and user.slack_user_id in settings.get_admin_ids('slack'):
            is_admin = True
            user_data["is_admin"] = True
        if user.telegram_id and str(user.telegram_id) in settings.get_admin_ids('telegram'):
            is_admin = True
            user_data["is_admin"] = True
        
        if user.is_superadmin:
            user_data["is_superadmin"] = True

        # Ensure UserAccount entry exists
        try:
            from app.repositories.user_account_repository import UserAccountRepository
            from app.repositories.user_repository import UserRepository
            from app.services.user_account_service import UserAccountService
            
            async with AsyncSessionLocal() as db:
                ua_service = UserAccountService(UserAccountRepository(db), UserRepository(db), db)
                await ua_service.find_or_create_account(
                    user_id=user.id,
                    provider='slack',
                    provider_id=user_info['user_id'],
                    workspace_id=user.workspace_id,
                    username=user_info.get('username')
                )
        except Exception as e:
            logger.warning(f"Failed to create/update UserAccount during Slack login: {e}")

        # Return bridge HTML to set user data and redirect to modern dashboard
        # Security: Session token is stored in httpOnly cookie only (not localStorage)
        # to protect against XSS attacks
        html = f"""
        <!DOCTYPE html>
        <html>
        <head><title>Redirecting...</title></head>
        <body>
            <script>
                // Store only non-sensitive user data for UI state
                localStorage.setItem('user', {json.dumps(json.dumps(user_data))});
                // Session token is in httpOnly cookie - DO NOT store in localStorage
                window.location.href = '/';
            </script>
        </body>
        </html>
        """
        response = HTMLResponse(content=html)
        # Determine if we're in production (use HTTPS)
        is_production = os.environ.get('ENVIRONMENT', 'development').lower() == 'production'
        response.set_cookie(
            "session_token",
            session_token,
            max_age=86400,
            httponly=True,
            samesite="Lax",
            secure=True  # Usually HTTPS via ngrok
        )
        logger.info(f"Setting session cookie and redirection bridge for Slack user {user.id}")

        # Clean up state
        if state in pending_states:
            del pending_states[state]

        return response

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in Slack callback: {e}", exc_info=True)
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/web/auth/logout")
@limiter.limit(get_rate_limit("auth_normal"))
async def logout(request: Request):
    """Logout user"""
    token = request.cookies.get('session_token')
    if token:
        await session_manager.revoke_session(token)

    response = RedirectResponse(url="/web/auth/login", status_code=302)
    response.delete_cookie("session_token")
    return response


@router.get("/web/auth/csrf-token")
async def get_csrf_token(request: Request):
    """
    Get CSRF token for making authenticated requests.

    The CSRF token must be included in state-changing requests (POST, PUT, DELETE)
    either as:
    - X-CSRF-Token header
    - csrf_token in request body (JSON or form data)

    Returns:
        JSON with csrf_token
    """
    csrf_token = csrf_protection.get_token_from_session(request)
    return {"csrf_token": csrf_token}


@router.get("/web/auth/workspaces")
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
                        
                        # Superadmin privilege: allow access to all their workspaces
                        is_allowed = is_admin or user_record.is_superadmin

                        # Filter: only show if admin, superadmin or master admin
                        if is_allowed:
                            workspaces.append({
                                'id': workspace.id,
                                'name': workspace.name,
                                'type': workspace.workspace_type,
                                'is_current': workspace.id == current_workspace_id,
                                'is_admin': is_admin,
                                'is_superadmin': user_record.is_superadmin,
                                'role': 'superadmin' if user_record.is_superadmin else ('admin' if is_admin else 'member')
                            })

            logger.info(f"User {user_id} has access to {len(workspaces)} workspace(s)")
            return {'workspaces': workspaces}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error listing workspaces: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to list workspaces")


@router.post("/web/auth/switch-workspace")
@limiter.limit(get_rate_limit("auth_normal"))
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
            'user': {
                'id': target_user.id,
                'username': target_user.username or target_user.telegram_username,
                'first_name': target_user.first_name,
                'last_name': target_user.last_name,
                'is_admin': is_admin,
                'is_superadmin': target_user.is_superadmin,
                'workspace_id': target_workspace_id,
            },
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
