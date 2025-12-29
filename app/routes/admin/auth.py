"""Authentication routes for web panel"""

import logging
import os
import secrets
from fastapi import APIRouter, Request, Response, HTTPException, Depends
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.auth import TelegramOAuth, SlackOAuth, session_manager
from app.models import User, Workspace
from app.database import AsyncSessionLocal
from app.middleware.rate_limiter import limiter, get_rate_limit
from app.middleware.csrf_protection import csrf_protection
from app.repositories import (
    UserRepository,
    UserAccountRepository,
    WorkspaceRepository,
)
from app.services.auth_service import AuthService
from app.utils.auth import (
    get_session_from_cookie,
    set_session_cookie,
    clear_session_cookie,
    build_user_data_json,
)
from app.utils.auth_templates import telegram_login_page, redirect_with_user_data

logger = logging.getLogger(__name__)
settings = get_settings()

router = APIRouter(tags=["web-auth"])

# OAuth providers
telegram_oauth = TelegramOAuth()
slack_oauth = SlackOAuth()

# Store pending states for CSRF protection
pending_states = {}


@router.get("/web/auth/login")
async def login_page(request: Request):
    """Login page - Redirect to modern React dashboard"""
    return RedirectResponse(url="/")


@router.get("/web/auth/telegram-login")
async def telegram_login(request: Request):
    """Telegram login redirect - show Telegram Web App login page"""
    return HTMLResponse(content=telegram_login_page())


@router.post("/web/auth/telegram-callback")
@limiter.limit(get_rate_limit("auth_strict"))
async def telegram_callback(request: Request):
    """Handle Telegram OAuth callback - validate and create/get user session"""
    try:
        form_data = await request.form()
        init_data = form_data.get("init_data")

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
            auth_service = AuthService(
                UserRepository(db),
                UserAccountRepository(db),
                WorkspaceRepository(db),
                db,
            )

<<<<<<< HEAD
            user, workspace = await auth_service.get_or_create_user_for_provider(
                provider="telegram",
                provider_id=str(user_info["user_id"]),
                user_info=user_info,
                allow_registration=True,
            )

            if not user or not workspace:
                raise HTTPException(status_code=401, detail="Failed to provision user")
=======
            # If not found by ID, try to find by username
            if not user and user_info.get('username'):
                logger.info(f"User not found by telegram_id, trying by username: {user_info.get('username')}")
                user_stmt = select(User).where(
                    (User.username == user_info.get('username')),
                    ((User.workspace_id == workspace.id) | 
                     ((User.organization_id == workspace.organization_id) & (User.organization_id != None)))
                ).order_by((User.workspace_id == workspace.id).desc())
                
                result = await db.execute(user_stmt)
                user = result.scalars().first()

                if user:
                    logger.info(f"Found existing user by username: {user.id}, linking Telegram ID {user_info['user_id']}")
                    # Create UserAccount
                    ua = UserAccount(
                        user_id=user.id,
                        workspace_id=workspace.id,
                        provider='telegram',
                        provider_id=str(user_info['user_id']),
                        username=user_info.get('username')
                    )
                    db.add(ua)
                    await db.commit()
                    await db.refresh(user)

            if not user:
                logger.info(f"Creating new user for Telegram ID {user_info['user_id']}")
                first_name = user_info.get('first_name')
                last_name = user_info.get('last_name')
                username = user_info.get('username')
                
                user = User(
                    workspace_id=workspace.id,
                    organization_id=workspace.organization_id,
                    username=username or str(user_info['user_id']),
                    first_name=first_name,
                    last_name=last_name,
                    display_name=f"{first_name or ''} {last_name or ''}".strip() or username or str(user_info['user_id'])
                )
                db.add(user)
                await db.commit()
                await db.refresh(user)
                
                # Create UserAccount
                user_account = UserAccount(
                    user_id=user.id,
                    workspace_id=workspace.id,
                    provider='telegram',
                    provider_id=str(user_info['user_id']),
                    username=username
                )
                db.add(user_account)
                await db.commit()
                logger.info(f"Created user: {user.id} and linked Telegram account")
            else:
                logger.info(f"Found existing user: {user.id}")
>>>>>>> origin/main

        # Create session
        session_token = await session_manager.create_session(
            user.id, workspace.id, "telegram"
        )
        logger.info(f"Created session token for user {user.id}")

        # Prepare user data for React
        async with AsyncSessionLocal() as db:
            auth_service = AuthService(
                UserRepository(db),
                UserAccountRepository(db),
                WorkspaceRepository(db),
                db,
            )
            user_data = auth_service.build_user_response(user, provider="telegram")

        # Return bridge HTML to set user data and redirect to modern dashboard
        html = redirect_with_user_data(build_user_data_json(user_data))
        response = HTMLResponse(content=html)

        # Determine if we're in production (use HTTPS)
        set_session_cookie(response, session_token, samesite="Lax")
        logger.info(f"Setting session cookie and redirection bridge for Telegram user {user.id}")
        return response

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in Telegram callback: {e}", exc_info=True)
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/web/auth/telegram-widget-callback")
@limiter.limit(get_rate_limit("auth_strict"))
async def telegram_widget_callback(request: Request):
    """Handle Telegram Login Widget callback (for web admin panel) - admins only"""
    try:
        logger.info("Telegram widget callback received")

        data = await request.json()
        logger.info(f"Widget callback data keys: {list(data.keys())}")

        if not data.get("id"):
            logger.error("No user ID provided in widget callback")
            raise HTTPException(status_code=400, detail="No user ID provided")

        # Validate the widget data
        logger.info("Validating widget data...")
        user_info = await telegram_oauth.validate_widget_data(data)
        if not user_info:
            logger.error("Failed to validate widget data")
            raise HTTPException(status_code=401, detail="Invalid Telegram authentication")

        logger.info(f"Widget validation successful")

        # Get or create user and workspace (admin panel only - no registration)
        async with AsyncSessionLocal() as db:
            auth_service = AuthService(
                UserRepository(db),
                UserAccountRepository(db),
                WorkspaceRepository(db),
                db,
            )

            user, workspace = await auth_service.get_or_create_user_for_provider(
                provider="telegram",
                provider_id=str(user_info["user_id"]),
                user_info=user_info,
                allow_registration=False,  # Admin panel - no auto-registration
            )

            if not user or not workspace:
                logger.warning(
                    f"User {user_info['user_id']} not found and registration is disabled"
                )
                raise HTTPException(
                    status_code=403,
                    detail="User not found. Please ask your administrator to add you to a team first.",
                )

            # Check admin status
            if not auth_service.check_admin_status(user, provider="telegram"):
                logger.warning(
                    f"User {user_info['user_id']} found but is not an admin in any workspace"
                )
                raise HTTPException(
                    status_code=403,
                    detail="Access denied. Only administrators can access the web panel.",
                )

        # Create session
        session_token = await session_manager.create_session(
            user.id, workspace.id, "telegram"
        )
        logger.info(f"Created session token for user {user.id}")

        # Build response
        async with AsyncSessionLocal() as db:
            auth_service = AuthService(
                UserRepository(db),
                UserAccountRepository(db),
                WorkspaceRepository(db),
                db,
            )
            user_data = auth_service.build_user_response(user, provider="telegram")

        response = JSONResponse(
            content={
                "success": True,
                "session_token": session_token,
                "user": {
                    **user_data,
                    "telegram_username": user.telegram_username,
                },
            }
        )

        # Ensure UserAccount entry exists
        async with AsyncSessionLocal() as db:
            auth_service = AuthService(
                UserRepository(db),
                UserAccountRepository(db),
                WorkspaceRepository(db),
                db,
            )
            await auth_service.ensure_user_account(
                user_id=user.id,
                provider="telegram",
                provider_id=str(user_info["user_id"]),
                workspace_id=user.workspace_id,
                username=user_info.get("username"),
            )

        # Set cookie for web panel
        set_session_cookie(response, session_token, samesite="Lax")

        logger.info(f"Returning success response with session cookie")
        return response

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in Telegram widget callback: {e}", exc_info=True)
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
    """Handle Slack OAuth callback - validate and create/get user session"""
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
            token_info["access_token"], token_info.get("user_id")
        )
        if not user_info:
            logger.error("Failed to get Slack user info")
            raise HTTPException(status_code=401, detail="Failed to get user info")

        logger.info(f"Validated Slack user: {user_info}")

        # Get or create user and workspace
        async with AsyncSessionLocal() as db:
            auth_service = AuthService(
                UserRepository(db),
                UserAccountRepository(db),
                WorkspaceRepository(db),
                db,
            )

            # Provide team info in user_info for workspace creation
            user_info["team_name"] = token_info.get("team_name")

            user, workspace = await auth_service.get_or_create_user_for_provider(
                provider="slack",
                provider_id=token_info["team_id"],
                user_info=user_info,
                allow_registration=True,
            )

            if not user or not workspace:
                raise HTTPException(status_code=401, detail="Failed to provision user")

            # Handle backwards compatibility: update names if missing
            if user.first_name or user.last_name or user.display_name:
                # User already has name info, skip update
                pass
            else:
                if user_info.get("first_name"):
                    user.first_name = user_info["first_name"]
                if user_info.get("last_name"):
                    user.last_name = user_info["last_name"]
                if user_info.get("display_name"):
                    user.display_name = user_info["display_name"]

<<<<<<< HEAD
=======
            # Get or create user with workspace_id set
            # 1. Try to find an existing account ALREADY in this workspace (any identity)
            user_stmt = select(User).join(UserAccount).where(
                UserAccount.provider == 'slack',
                UserAccount.provider_id == user_info['user_id'],
                UserAccount.workspace_id == workspace.id
            )
            result = await db.execute(user_stmt)
            user = result.scalars().first()

            if user:
                logger.info(f"Found existing user {user.id} with Slack account in workspace {workspace.id}")
            else:
                # 2. Search for existing identity via this Slack ID across ANY workspace
                user_stmt = select(User).join(UserAccount).where(
                    UserAccount.provider == 'slack',
                    UserAccount.provider_id == user_info['user_id']
                ).order_by(User.is_superadmin.desc(), User.is_admin.desc())
                result = await db.execute(user_stmt)
                user = result.scalars().first()
                
                if user:
                    logger.info(f"Found existing identity {user.id} via Slack ID elsewhere, linking to workspace {workspace.id}")
                    # Link to this workspace
                    ua = UserAccount(
                        user_id=user.id,
                        workspace_id=workspace.id,
                        provider='slack',
                        provider_id=user_info['user_id'],
                        username=user_info.get('username')
                    )
                    db.add(ua)
                    await db.commit()
                    await db.refresh(user)
                else:
                    # 3. Search by username in the same Organization or workspace
                    logger.info(f"User not found by id, trying by username: {user_info.get('username')}")
                    user_stmt = select(User).where(
                        (User.username == user_info.get('username')),
                        ((User.workspace_id == workspace.id) | 
                         ((User.organization_id == workspace.organization_id) & (User.organization_id != None)))
                    ).order_by((User.workspace_id == workspace.id).desc())
                    
                    result = await db.execute(user_stmt)
                    user = result.scalars().first()

                    if user:
                        logger.info(f"Found existing user by username: {user.id}, linking Slack ID {user_info['user_id']}")
                        # Create UserAccount
                        ua = UserAccount(
                            user_id=user.id,
                            workspace_id=workspace.id,
                            provider='slack',
                            provider_id=user_info['user_id'],
                            username=user_info.get('username')
                        )
                        db.add(ua)
                        await db.commit()
                        await db.refresh(user)

            if not user:
                logger.info(f"Creating new user for Slack user ID {user_info['user_id']}")
                user = User(
                    workspace_id=workspace.id,
                    organization_id=workspace.organization_id,
                    username=user_info.get('username'),
                    first_name=user_info.get('first_name'),
                    last_name=user_info.get('last_name'),
                    display_name=user_info.get('display_name') or user_info.get('real_name') or user_info.get('username')
                )
                db.add(user)
>>>>>>> origin/main
                await db.commit()
                await db.refresh(user)

        # Create session
        session_token = await session_manager.create_session(
            user.id, workspace.id, "slack"
        )
        logger.info(f"Created session token for user {user.id}")

        # Prepare user data for React
        async with AsyncSessionLocal() as db:
            auth_service = AuthService(
                UserRepository(db),
                UserAccountRepository(db),
                WorkspaceRepository(db),
                db,
            )
            user_data = auth_service.build_user_response(user, provider="slack")

        # Ensure UserAccount entry exists
        async with AsyncSessionLocal() as db:
            auth_service = AuthService(
                UserRepository(db),
                UserAccountRepository(db),
                WorkspaceRepository(db),
                db,
            )
            await auth_service.ensure_user_account(
                user_id=user.id,
                provider="slack",
                provider_id=user_info["user_id"],
                workspace_id=user.workspace_id,
                username=user_info.get("username"),
            )

        # Return bridge HTML to set user data and redirect to modern dashboard
        html = redirect_with_user_data(build_user_data_json(user_data))
        response = HTMLResponse(content=html)

        # Slack requires SameSite=None with Secure for cross-site cookies
        set_session_cookie(response, session_token, samesite="None")
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
    """Logout user - revoke session and clear cookies"""
    token = request.cookies.get("session_token")
    if token:
        await session_manager.revoke_session(token)

    response = RedirectResponse(url="/web/auth/login", status_code=302)
    clear_session_cookie(response)
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
async def list_workspaces(
    request: Request, session: dict = Depends(get_session_from_cookie)
):
    """Get list of workspaces where current user has admin/superadmin access"""
    try:
        user_id = session["user_id"]
        current_workspace_id = session["workspace_id"]

        async with AsyncSessionLocal() as db:
            # Get current user
            current_user = await db.get(User, user_id)
            if not current_user:
                raise HTTPException(status_code=404, detail="User not found")

            # Find all user records for this user (across all workspaces)
            auth_service = AuthService(
                UserRepository(db),
                UserAccountRepository(db),
                WorkspaceRepository(db),
                db,
            )

            # Build list of all user records for this platform ID
            user_records = []

            if current_user.telegram_id:
                stmt = (
                    select(User)
                    .join(UserAccount)
                    .where(
                        UserAccount.provider == "telegram",
                        UserAccount.provider_id == str(current_user.telegram_id),
                    )
                )
            elif current_user.slack_user_id:
                stmt = (
                    select(User)
                    .join(UserAccount)
                    .where(
                        UserAccount.provider == "slack",
                        UserAccount.provider_id == current_user.slack_user_id,
                    )
                )
            else:
                raise HTTPException(status_code=400, detail="User has no platform ID")

            result = await db.execute(stmt)
            user_records = result.scalars().all()

            # Build workspace list
            workspaces = []
            workspace_ids = set()

            for user_record in user_records:
                if user_record.workspace_id in workspace_ids:
                    continue

                workspace_ids.add(user_record.workspace_id)
                workspace = await db.get(Workspace, user_record.workspace_id)
                if not workspace:
                    continue

                # Check if user has access (admin, superadmin, or master admin)
                is_admin = auth_service.check_admin_status(user_record)

                if is_admin or user_record.is_superadmin:
                    role = (
                        "superadmin"
                        if user_record.is_superadmin
                        else ("admin" if is_admin else "member")
                    )
                    workspaces.append(
                        {
                            "id": workspace.id,
                            "name": workspace.name,
                            "type": workspace.workspace_type,
                            "is_current": workspace.id == current_workspace_id,
                            "is_admin": is_admin,
                            "is_superadmin": user_record.is_superadmin,
                            "role": role,
                        }
                    )

            logger.info(f"User {user_id} has access to {len(workspaces)} workspace(s)")
            return {"workspaces": workspaces}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error listing workspaces: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to list workspaces")


@router.post("/web/auth/switch-workspace")
@limiter.limit(get_rate_limit("auth_normal"))
async def switch_workspace(
    request: Request, session: dict = Depends(get_session_from_cookie)
):
    """Switch to a different workspace.

    Request body: {"workspace_id": <id>}
    Response: New session token for target workspace
    """
    try:
        user_id = session["user_id"]
        current_workspace_id = session["workspace_id"]

        data = await request.json()
        target_workspace_id = data.get("workspace_id")

        if not target_workspace_id:
            raise HTTPException(status_code=400, detail="Missing workspace_id")

        if target_workspace_id == current_workspace_id:
            logger.info(f"User {user_id} already in workspace {target_workspace_id}")
            return {
                "session_token": request.cookies.get("session_token"),
                "message": "Already in this workspace",
            }

        async with AsyncSessionLocal() as db:
            # Get current user to get their platform ID
            current_user = await db.get(User, user_id)
            if not current_user:
                raise HTTPException(status_code=404, detail="User not found")

            auth_service = AuthService(
                UserRepository(db),
                UserAccountRepository(db),
                WorkspaceRepository(db),
                db,
            )

            # Find user record in target workspace with same platform ID
            if current_user.telegram_id:
                target_user_stmt = (
                    select(User)
                    .join(UserAccount)
                    .where(
                        UserAccount.provider == "telegram",
                        UserAccount.provider_id == str(current_user.telegram_id),
                        User.workspace_id == target_workspace_id,
                    )
                )
            elif current_user.slack_user_id:
                target_user_stmt = (
                    select(User)
                    .join(UserAccount)
                    .where(
                        UserAccount.provider == "slack",
                        UserAccount.provider_id == current_user.slack_user_id,
                        User.workspace_id == target_workspace_id,
                    )
                )
            else:
                raise HTTPException(status_code=400, detail="User has no platform ID")

            result = await db.execute(target_user_stmt)
            target_user = result.scalar_one_or_none()

            if not target_user:
                logger.warning(
                    f"User {user_id} not found in target workspace {target_workspace_id}"
                )
                raise HTTPException(status_code=403, detail="Access denied to this workspace")

            # Check admin status for the target workspace
            is_admin = auth_service.check_admin_status(target_user)

            if not is_admin and not target_user.is_superadmin:
                logger.warning(
                    f"User {user_id} attempted to switch to workspace {target_workspace_id} without admin rights"
                )
                raise HTTPException(
                    status_code=403,
                    detail="You do not have administrator permissions in this workspace",
                )

            # Verify workspace exists
            target_workspace = await db.get(Workspace, target_workspace_id)
            if not target_workspace:
                raise HTTPException(status_code=404, detail="Workspace not found")

            logger.info(
                f"Switching user {user_id} from workspace {current_workspace_id} to {target_workspace_id}"
            )

        # Create new session for target workspace
        new_token = await session_manager.create_session(
            target_user.id, target_workspace_id, target_workspace.workspace_type
        )

        async with AsyncSessionLocal() as db:
            auth_service = AuthService(
                UserRepository(db),
                UserAccountRepository(db),
                WorkspaceRepository(db),
                db,
            )
            user_data = auth_service.build_user_response(target_user)

        response = JSONResponse(
            content={
                "success": True,
                "session_token": new_token,
                "user": user_data,
                "workspace": {
                    "id": target_workspace_id,
                    "name": target_workspace.name,
                    "type": target_workspace.workspace_type,
                },
            }
        )

        set_session_cookie(response, new_token, samesite="Lax")

        return response

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error switching workspace: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to switch workspace")
