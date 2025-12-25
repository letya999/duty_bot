"""Session management module for web authentication"""
import logging
import secrets
from datetime import datetime, timedelta
from typing import Optional, Dict, Any

from app.database import AsyncSessionLocal
from app.models import User

logger = logging.getLogger(__name__)


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
