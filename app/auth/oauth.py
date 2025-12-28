"""OAuth authentication providers - Telegram and Slack"""
import hashlib
import hmac
import json
import logging
from datetime import datetime
from typing import Optional, Dict, Any
import aiohttp

from app.config import get_settings

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
            logger.info(f"🔵 [Validate] Starting widget data validation")
            logger.info(f"🔵 [Validate] Received data keys: {list(data.keys())}")
            logger.info(f"🔵 [Validate] Data: {data}")

            # Get hash from data
            data_hash = data.get('hash')
            logger.info(f"🔵 [Validate] Hash from data: {data_hash[:10]}..." if data_hash else "🔵 [Validate] Hash: MISSING")

            if not data_hash:
                logger.warning("❌ [Validate] No hash in widget data")
                return None

            # Create data check string (exclude hash)
            data_list = []
            for key in sorted(data.keys()):
                if key != 'hash' and data[key] is not None:
                    value = data[key]
                    if isinstance(value, bool):
                        value = "true" if value else "false"
                    data_list.append(f"{key}={value}")
            data_check_string = '\n'.join(data_list)

            logger.info(f"🔵 [Validate] Data check string: {data_check_string[:100]}...")

            # Validate signature
            secret_key = hashlib.sha256(settings.telegram_token.encode()).digest()
            expected_hash = hmac.new(
                secret_key,
                data_check_string.encode(),
                hashlib.sha256
            ).hexdigest()

            logger.info(f"🔵 [Validate] Expected hash: {expected_hash[:20]}...")
            logger.info(f"🔵 [Validate] Actual hash:   {data_hash[:20]}...")

            if data_hash != expected_hash:
                logger.warning(f"❌ [Validate] Invalid hash: {data_hash} != {expected_hash}")
                # FALLBACK: If hash fails but we define a DEV_BYPASS_AUTH_ID in env, allow it (for testing only)
                # But for now, strictly enforce hash.
                # Common issue: URL decoding of special chars. Web widget sends raw strings.
                return None

            logger.info("✅ [Validate] Hash valid, returning user data")

            # Check if data is not too old (max 1 day)
            auth_date = int(data.get('auth_date', 0))
            if datetime.now().timestamp() - auth_date > 86400:
                logger.warning("❌ [Validate] Telegram auth data too old")
                return None

            return {
                'platform': 'telegram',
                'user_id': int(data.get('id')),
                'username': data.get('username'),
                'first_name': data.get('first_name'),
                'last_name': data.get('last_name'),
                'auth_date': auth_date,
            }

        except Exception as e:
            logger.error(f"❌ [Validate] Error validating Telegram widget data: {e}", exc_info=True)
            return None


class SlackOAuth(OAuthProvider):
    """Slack OAuth provider"""

    async def get_auth_url(self, state: str) -> str:
        """Get Slack authorization URL"""
        return (
            f"https://slack.com/oauth/v2/authorize?"
            f"client_id={settings.slack_client_id}&"
            f"scope=users:read,users:read.email&"
            f"state={state}&"
            f"redirect_uri={settings.slack_redirect_uri}"
        )

    async def exchange_code_for_token(self, code: str) -> Dict[str, Any]:
        """Exchange authorization code for Slack access token"""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    "https://slack.com/api/oauth.v2.access",
                    data={
                        "client_id": settings.slack_client_id,
                        "client_secret": settings.slack_client_secret,
                        "code": code,
                        "redirect_uri": settings.slack_redirect_uri,
                    }
                ) as resp:
                    data = await resp.json()
                    if not data.get('ok'):
                        logger.error(f"Slack OAuth error: {data.get('error')}")
                        return {}
                    return {
                        'access_token': data.get('access_token'),
                        'team_id': data.get('team', {}).get('id'),
                        'team_name': data.get('team', {}).get('name'),
                        'user_id': data.get('authed_user', {}).get('id'),
                    }
        except Exception as e:
            logger.error(f"Error exchanging Slack code: {e}")
            return {}

    async def get_user_info(self, token: str) -> Dict[str, Any]:
        """Get user info from Slack"""
        try:
            async with aiohttp.ClientSession() as session:
                # First, get the authenticated user ID via auth.test
                async with session.get(
                    "https://slack.com/api/auth.test",
                    headers={"Authorization": f"Bearer {token}"}
                ) as resp:
                    auth_data = await resp.json()
                    if not auth_data.get('ok'):
                        logger.error(f"Slack auth.test error: {auth_data.get('error')}")
                        return {}
                    user_id = auth_data.get('user_id')

                # Then get user info via users.info
                async with session.get(
                    "https://slack.com/api/users.info",
                    headers={"Authorization": f"Bearer {token}"},
                    params={"user": user_id}
                ) as resp:
                    data = await resp.json()
                    if not data.get('ok'):
                        logger.error(f"Slack API error: {data.get('error')}")
                        return {}

                    user_obj = data.get('user', {})
                    profile = user_obj.get('profile', {})

                    return {
                        'platform': 'slack',
                        'user_id': user_obj.get('id'),
                        'username': user_obj.get('name'),
                        'email': profile.get('email'),
                        'real_name': user_obj.get('real_name'),
                        'first_name': profile.get('first_name'),
                        'last_name': profile.get('last_name'),
                        'workspace_id': auth_data.get('team_id'),
                    }
        except Exception as e:
            logger.error(f"Error getting Slack user info: {e}")
            return {}
