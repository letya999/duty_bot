"""Authentication module - OAuth and session management"""
from app.auth.oauth import OAuthProvider, TelegramOAuth, SlackOAuth
from app.auth.session import SessionManager, session_manager, get_or_create_user

__all__ = [
    'OAuthProvider',
    'TelegramOAuth',
    'SlackOAuth',
    'SessionManager',
    'session_manager',
    'get_or_create_user',
]
