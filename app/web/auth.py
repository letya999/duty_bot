"""OAuth authentication module for web panel"""
import hashlib
import hmac
import json
import logging
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
import secrets
import aiohttp

from app.config import get_settings
from app.database import AsyncSessionLocal
from app.models import User, Workspace

logger = logging.getLogger(__name__)
settings = get_settings()


class OAuthProvider:
    """Base OAuth provider class"""

    async def get_auth_url(self, state: str) -> str:
        """Get authorization URL"""
        raise NotImplementedError

    async def exchange_code_for_token(self, code: str) -> Dict[str, Any]:
        """Exchange authorization code for access token"""
        raise NotImplementedError

    async def get_user_info(self, token: str) -> Dict[str, Any]:
        """Get user info from provider"""
        raise NotImplementedError


class TelegramOAuth(OAuthProvider):
    """Telegram OAuth provider using bot token validation"""

    async def validate_init_data(self, init_data: str) -> Optional[Dict[str, Any]]:
        """Validate Telegram mini app init data"""
        try:
            # Parse query string
            params = {}
            for item in init_data.split('&'):
                key, value = item.split('=')
                params[key] = value

            # Get hash
            data_check_string = '\n'.join(
                f"{k}={v}" for k, v in sorted(params.items()) if k != 'hash'
            )

            # Validate signature
            expected_hash = hmac.new(
                hashlib.sha256(settings.telegram_token.encode()).digest(),
                data_check_string.encode(),
                hashlib.sha256
            ).hexdigest()

            if params.get('hash') != expected_hash:
                logger.warning(f"Invalid Telegram signature: {params.get('hash')} != {expected_hash}")
                return None

            # Check if data is not too old (max 1 day)
            auth_date = int(params.get('auth_date', 0))
            if datetime.now().timestamp() - auth_date > 86400:
                logger.warning("Telegram auth data too old")
                return None

            # Parse user data
            if 'user' not in params:
                return None

            user_data = json.loads(params['user'])
            return {
                'platform': 'telegram',
                'user_id': user_data.get('id'),
                'username': user_data.get('username'),
                'first_name': user_data.get('first_name'),
                'last_name': user_data.get('last_name'),
                'language_code': user_data.get('language_code'),
            }
        except Exception as e:
            logger.error(f"Error validating Telegram init data: {e}")
            return None

    async def validate_widget_data(self, data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Validate Telegram Login Widget data"""
        try:
            # Get hash from data
            data_hash = data.get('hash')
            if not data_hash:
                logger.warning("No hash in widget data")
                return None

            # Create data check string - must be sorted alphabetically and exclude hash
            data_check_list = []
            for key in sorted(data.keys()):
                if key != 'hash':
                    data_check_list.append(f"{key}={data[key]}")

            data_check_string = '\n'.join(data_check_list)

            # Validate signature using bot token
            secret = hashlib.sha256(settings.telegram_token.encode()).digest()
            expected_hash = hmac.new(
                secret,
                data_check_string.encode(),
                hashlib.sha256
            ).hexdigest()

            if data_hash != expected_hash:
                logger.warning(f"Invalid widget signature: {data_hash} != {expected_hash}")
                return None

            # Check if data is not too old (max 1 day)
            auth_date = int(data.get('auth_date', 0))
            if datetime.now().timestamp() - auth_date > 86400:
                logger.warning("Widget auth data too old")
                return None

            return {
                'platform': 'telegram',
                'user_id': data.get('id'),
                'username': data.get('username'),
                'first_name': data.get('first_name'),
                'last_name': data.get('last_name'),
                'language_code': data.get('language_code'),
            }
        except Exception as e:
            logger.error(f"Error validating widget data: {e}")
            return None


class SlackOAuth(OAuthProvider):
    """Slack OAuth provider"""

    def __init__(self):
        self.client_id = settings.slack_client_id
        self.client_secret = settings.slack_client_secret
        self.redirect_uri = settings.slack_redirect_uri

    async def get_auth_url(self, state: str) -> str:
        """Get Slack authorization URL"""
        return (
            f"https://slack.com/oauth/v2/authorize?"
            f"client_id={self.client_id}&"
            f"redirect_uri={self.redirect_uri}&"
            f"scope=chat:write,users:read,users:read.email&"
            f"state={state}"
        )

    async def exchange_code_for_token(self, code: str) -> Optional[Dict[str, Any]]:
        """Exchange authorization code for access token"""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    'https://slack.com/api/oauth.v2.access',
                    data={
                        'client_id': self.client_id,
                        'client_secret': self.client_secret,
                        'code': code,
                        'redirect_uri': self.redirect_uri,
                    }
                ) as resp:
                    data = await resp.json()
                    if data.get('ok'):
                        return {
                            'access_token': data.get('access_token'),
                            'token_type': data.get('token_type'),
                            'scope': data.get('scope'),
                            'team_id': data.get('team', {}).get('id'),
                            'team_name': data.get('team', {}).get('name'),
                        }
                    else:
                        logger.error(f"Slack OAuth error: {data.get('error')}")
                        return None
        except Exception as e:
            logger.error(f"Error exchanging Slack code: {e}")
            return None

    async def get_user_info(self, token: str) -> Optional[Dict[str, Any]]:
        """Get Slack user info"""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    'https://slack.com/api/auth.test',
                    headers={'Authorization': f'Bearer {token}'}
                ) as resp:
                    data = await resp.json()
                    if data.get('ok'):
                        return {
                            'platform': 'slack',
                            'user_id': data.get('user_id'),
                            'username': data.get('user'),
                            'team_id': data.get('team_id'),
                            'team_name': data.get('team'),
                        }
                    else:
                        logger.error(f"Slack auth.test error: {data.get('error')}")
                        return None
        except Exception as e:
            logger.error(f"Error getting Slack user info: {e}")
            return None


class SessionManager:
    """Manage user sessions"""

    def __init__(self, session_timeout_hours: int = 24):
        self.session_timeout = timedelta(hours=session_timeout_hours)
        self.sessions: Dict[str, Dict[str, Any]] = {}

    def create_session(self, user_id: int, workspace_id: int, platform: str) -> str:
        """Create a new session token"""
        token = secrets.token_urlsafe(32)
        self.sessions[token] = {
            'user_id': user_id,
            'workspace_id': workspace_id,
            'platform': platform,
            'created_at': datetime.now(),
            'expires_at': datetime.now() + self.session_timeout,
        }
        return token

    def validate_session(self, token: str) -> Optional[Dict[str, Any]]:
        """Validate session token"""
        if token not in self.sessions:
            return None

        session = self.sessions[token]
        if datetime.now() > session['expires_at']:
            del self.sessions[token]
            return None

        return session

    def revoke_session(self, token: str) -> bool:
        """Revoke a session"""
        if token in self.sessions:
            del self.sessions[token]
            return True
        return False

    def refresh_session(self, token: str) -> Optional[str]:
        """Refresh session expiration"""
        session = self.validate_session(token)
        if not session:
            return None

        # Create new token with same data
        new_token = secrets.token_urlsafe(32)
        self.sessions[new_token] = {
            **session,
            'created_at': datetime.now(),
            'expires_at': datetime.now() + self.session_timeout,
        }

        # Revoke old token
        self.revoke_session(token)
        return new_token


# Global session manager
session_manager = SessionManager()


async def get_or_create_user(platform: str, user_info: Dict[str, Any]) -> Optional[User]:
    """Get or create user from OAuth info"""
    async with AsyncSessionLocal() as session:
        try:
            if platform == 'telegram':
                # Try to find existing user
                from sqlalchemy import select
                stmt = select(User).where(
                    User.telegram_id == user_info['user_id']
                )
                result = await session.execute(stmt)
                user = result.scalars().first()

                if not user:
                    # Create new user
                    user = User(
                        telegram_id=user_info['user_id'],
                        username=user_info.get('username', ''),
                        first_name=user_info.get('first_name', ''),
                        last_name=user_info.get('last_name', ''),
                        workspace_id=None,  # Will be set during workspace selection
                    )
                    session.add(user)
                    await session.commit()

                return user

            elif platform == 'slack':
                from sqlalchemy import select
                stmt = select(User).where(
                    User.slack_user_id == user_info['user_id']
                )
                result = await session.execute(stmt)
                user = result.scalars().first()

                if not user:
                    user = User(
                        slack_user_id=user_info['user_id'],
                        username=user_info.get('username', ''),
                        workspace_id=None,
                    )
                    session.add(user)
                    await session.commit()

                return user

        except Exception as e:
            logger.error(f"Error getting or creating user: {e}")
            return None
