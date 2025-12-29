"""Authentication module - OAuth and session management"""
from app.auth.oauth import OAuthProvider, TelegramOAuth, SlackOAuth
from app.auth.session_persistent import PersistentSessionManager
from app.auth.session import get_or_create_user

# Create persistent session manager instance
session_manager = PersistentSessionManager()

__all__ = [
    'OAuthProvider',
    'TelegramOAuth',
    'SlackOAuth',
    'PersistentSessionManager',
    'session_manager',
    'get_or_create_user',
]
