"""Persistent Session Management with Redis and Database fallback

This module provides session storage that persists across application restarts.
It uses Redis when available for optimal performance, with automatic fallback
to database storage.
"""

import json
import logging
import secrets
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
import os

logger = logging.getLogger(__name__)


class PersistentSessionManager:
    """
    Manage user sessions with persistent storage.

    Storage Priority:
    1. Redis (if available) - Fast, in-memory storage
    2. Database (fallback) - Reliable, persistent storage
    3. In-memory (emergency fallback) - For development/testing
    """

    def __init__(self, session_timeout_hours: int = 24):
        self.session_timeout = timedelta(hours=session_timeout_hours)
        self.timeout_seconds = int(session_timeout_hours * 3600)
        self.redis_client = None
        self.use_redis = False
        self.use_database = False
        self.sessions: Dict[str, Dict[str, Any]] = {}  # Emergency fallback

        self._initialize_storage()

    def _initialize_storage(self):
        """Initialize storage backend (Redis, Database, or in-memory)"""
        # Try Redis first
        redis_url = os.environ.get('REDIS_URL', os.environ.get('REDIS_URI'))
        if redis_url:
            try:
                import redis.asyncio as redis
                self.redis_client = redis.from_url(
                    redis_url,
                    encoding="utf-8",
                    decode_responses=True
                )
                self.use_redis = True
                logger.info("✅ Session storage: Redis (optimal)")
                return
            except ImportError:
                logger.warning("Redis library not available, falling back to database")
            except Exception as e:
                logger.warning(f"Failed to connect to Redis: {e}, falling back to database")

        # Fallback to database
        try:
            from app.models import Session as SessionModel
            self.use_database = True
            logger.info("✅ Session storage: Database (fallback)")
            return
        except Exception as e:
            logger.warning(f"Database session storage failed: {e}")

        # Emergency fallback to in-memory
        logger.warning("⚠️  Session storage: In-memory (not persistent, dev only)")

    async def create_session(self, user_id: int, workspace_id: int, platform: str) -> str:
        """Create a new session token"""
        token = secrets.token_urlsafe(32)
        session_data = {
            'user_id': user_id,
            'workspace_id': workspace_id,
            'platform': platform,
            'created_at': datetime.now().isoformat(),
            'expires_at': (datetime.now() + self.session_timeout).isoformat(),
        }

        if self.use_redis and self.redis_client:
            try:
                # Store in Redis with TTL
                await self.redis_client.setex(
                    f"session:{token}",
                    self.timeout_seconds,
                    json.dumps(session_data)
                )
                return token
            except Exception as e:
                logger.error(f"Redis session creation failed: {e}, falling back")

        if self.use_database:
            try:
                from app.database import AsyncSessionLocal
                from app.models import Session as SessionModel
                async with AsyncSessionLocal() as db:
                    db_session = SessionModel(
                        token=token,
                        user_id=user_id,
                        workspace_id=workspace_id,
                        platform=platform,
                        expires_at=datetime.now() + self.session_timeout
                    )
                    db.add(db_session)
                    await db.commit()
                    return token
            except Exception as e:
                logger.error(f"Database session creation failed: {e}, using memory")

        # Emergency fallback
        self.sessions[token] = session_data
        return token

    async def validate_session(self, token: str) -> Optional[Dict[str, Any]]:
        """Validate session token and return session data"""
        if self.use_redis and self.redis_client:
            try:
                data = await self.redis_client.get(f"session:{token}")
                if data:
                    session = json.loads(data)
                    # Check expiration
                    expires_at = datetime.fromisoformat(session['expires_at'])
                    if datetime.now() < expires_at:
                        return session
                    # Session expired, delete it
                    await self.redis_client.delete(f"session:{token}")
                return None
            except Exception as e:
                logger.error(f"Redis session validation failed: {e}")

        if self.use_database:
            try:
                from app.database import AsyncSessionLocal
                from app.models import Session as SessionModel
                from sqlalchemy import select
                async with AsyncSessionLocal() as db:
                    stmt = select(SessionModel).where(SessionModel.token == token)
                    result = await db.execute(stmt)
                    db_session = result.scalars().first()

                    if db_session:
                        # Check expiration
                        if datetime.now() < db_session.expires_at:
                            return {
                                'user_id': db_session.user_id,
                                'workspace_id': db_session.workspace_id,
                                'platform': db_session.platform,
                                'created_at': db_session.created_at.isoformat(),
                                'expires_at': db_session.expires_at.isoformat(),
                            }
                        # Session expired, delete it
                        await db.delete(db_session)
                        await db.commit()
                return None
            except Exception as e:
                logger.error(f"Database session validation failed: {e}")

        # Emergency fallback
        if token in self.sessions:
            session = self.sessions[token]
            expires_at = datetime.fromisoformat(session['expires_at'])
            if datetime.now() < expires_at:
                return session
            del self.sessions[token]
        return None

    async def revoke_session(self, token: str) -> bool:
        """Revoke a session"""
        if self.use_redis and self.redis_client:
            try:
                result = await self.redis_client.delete(f"session:{token}")
                return result > 0
            except Exception as e:
                logger.error(f"Redis session revocation failed: {e}")

        if self.use_database:
            try:
                from app.database import AsyncSessionLocal
                from app.models import Session as SessionModel
                from sqlalchemy import select
                async with AsyncSessionLocal() as db:
                    stmt = select(SessionModel).where(SessionModel.token == token)
                    result = await db.execute(stmt)
                    db_session = result.scalars().first()
                    if db_session:
                        await db.delete(db_session)
                        await db.commit()
                        return True
                return False
            except Exception as e:
                logger.error(f"Database session revocation failed: {e}")

        # Emergency fallback
        if token in self.sessions:
            del self.sessions[token]
            return True
        return False

    async def refresh_session(self, token: str) -> Optional[str]:
        """Refresh session expiration"""
        session = await self.validate_session(token)
        if not session:
            return None

        # Create new token with same data
        new_token = secrets.token_urlsafe(32)
        new_session_data = {
            **session,
            'created_at': datetime.now().isoformat(),
            'expires_at': (datetime.now() + self.session_timeout).isoformat(),
        }

        if self.use_redis and self.redis_client:
            try:
                # Store new session
                await self.redis_client.setex(
                    f"session:{new_token}",
                    self.timeout_seconds,
                    json.dumps(new_session_data)
                )
                # Delete old session
                await self.redis_client.delete(f"session:{token}")
                return new_token
            except Exception as e:
                logger.error(f"Redis session refresh failed: {e}")

        if self.use_database:
            try:
                from app.database import AsyncSessionLocal
                from app.models import Session as SessionModel
                from sqlalchemy import select
                async with AsyncSessionLocal() as db:
                    # Create new session
                    new_db_session = SessionModel(
                        token=new_token,
                        user_id=session['user_id'],
                        workspace_id=session['workspace_id'],
                        platform=session['platform'],
                        expires_at=datetime.now() + self.session_timeout
                    )
                    db.add(new_db_session)

                    # Delete old session
                    stmt = select(SessionModel).where(SessionModel.token == token)
                    result = await db.execute(stmt)
                    old_session = result.scalars().first()
                    if old_session:
                        await db.delete(old_session)

                    await db.commit()
                    return new_token
            except Exception as e:
                logger.error(f"Database session refresh failed: {e}")

        # Emergency fallback
        self.sessions[new_token] = new_session_data
        if token in self.sessions:
            del self.sessions[token]
        return new_token

    async def revoke_all_user_sessions(self, user_id: int) -> int:
        """Revoke all sessions for a user"""
        count = 0

        if self.use_redis and self.redis_client:
            try:
                # Scan for all sessions and check user_id
                cursor = 0
                while True:
                    cursor, keys = await self.redis_client.scan(cursor, match="session:*")
                    for key in keys:
                        data = await self.redis_client.get(key)
                        if data:
                            session = json.loads(data)
                            if session.get('user_id') == user_id:
                                await self.redis_client.delete(key)
                                count += 1
                    if cursor == 0:
                        break
                return count
            except Exception as e:
                logger.error(f"Redis bulk revocation failed: {e}")

        if self.use_database:
            try:
                from app.database import AsyncSessionLocal
                from app.models import Session as SessionModel
                from sqlalchemy import select, delete
                async with AsyncSessionLocal() as db:
                    stmt = delete(SessionModel).where(SessionModel.user_id == user_id)
                    result = await db.execute(stmt)
                    await db.commit()
                    return result.rowcount
            except Exception as e:
                logger.error(f"Database bulk revocation failed: {e}")

        # Emergency fallback
        tokens_to_delete = [
            token for token, session in self.sessions.items()
            if session.get('user_id') == user_id
        ]
        for token in tokens_to_delete:
            del self.sessions[token]
            count += 1
        return count

    async def get_user_from_token(self, token: str, user_repo) -> Optional[Any]:
        """Get user object from session token"""
        session = await self.validate_session(token)
        if not session:
            return None

        return await user_repo.get_by_id(session['user_id'])

    async def cleanup_expired_sessions(self) -> int:
        """Clean up expired sessions (for database storage)"""
        if not self.use_database:
            return 0

        try:
            from app.database import AsyncSessionLocal
            from app.models import Session as SessionModel
            from sqlalchemy import delete
            async with AsyncSessionLocal() as db:
                stmt = delete(SessionModel).where(SessionModel.expires_at < datetime.now())
                result = await db.execute(stmt)
                await db.commit()
                return result.rowcount
        except Exception as e:
            logger.error(f"Session cleanup failed: {e}")
            return 0
