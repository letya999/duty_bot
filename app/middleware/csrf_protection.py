"""CSRF Protection Middleware

Protects against Cross-Site Request Forgery (CSRF) attacks by validating
tokens on state-changing requests (POST, PUT, DELETE, PATCH).
"""

import hmac
import secrets
from typing import Optional
from fastapi import Request, HTTPException
from itsdangerous import URLSafeTimedSerializer, BadSignature, SignatureExpired
import logging
import os

logger = logging.getLogger(__name__)


class CSRFProtection:
    """
    CSRF Protection for FastAPI applications.

    This class provides CSRF token generation and validation to protect
    against Cross-Site Request Forgery attacks.
    """

    def __init__(self, secret_key: Optional[str] = None, token_lifetime: int = 3600):
        """
        Initialize CSRF protection.

        Args:
            secret_key: Secret key for signing tokens (uses SECRET_KEY from env if not provided)
            token_lifetime: Token lifetime in seconds (default: 1 hour)
        """
        self.secret_key = secret_key or os.environ.get('SECRET_KEY', secrets.token_urlsafe(32))
        self.token_lifetime = token_lifetime
        self.serializer = URLSafeTimedSerializer(self.secret_key, salt='csrf')

        # Methods that require CSRF protection
        self.protected_methods = {'POST', 'PUT', 'DELETE', 'PATCH'}

        # Paths that are exempt from CSRF protection
        self.exempt_paths = {
            '/api/docs',
            '/api/openapi.json',
            '/api/redoc',
            '/api/admin/auth/slack/callback',  # OAuth callbacks use state parameter
            '/web/auth/telegram-callback',  # Telegram OAuth
            '/web/auth/telegram-widget-callback',  # Telegram widget
        }

    def generate_token(self, session_token: Optional[str] = None) -> str:
        """
        Generate a CSRF token.

        Args:
            session_token: Optional session token to bind CSRF token to

        Returns:
            CSRF token string
        """
        # Generate random token
        token_data = {
            'random': secrets.token_urlsafe(16),
            'session': session_token[:8] if session_token else None,  # Bind to session
        }

        return self.serializer.dumps(token_data)

    def validate_token(self, csrf_token: str, session_token: Optional[str] = None) -> bool:
        """
        Validate a CSRF token.

        Args:
            csrf_token: CSRF token to validate
            session_token: Optional session token to verify binding

        Returns:
            True if token is valid, False otherwise
        """
        try:
            # Verify and decode token (with expiration check)
            token_data = self.serializer.loads(csrf_token, max_age=self.token_lifetime)

            # If session binding is enabled, verify it matches
            if session_token and token_data.get('session'):
                session_prefix = session_token[:8]
                if token_data['session'] != session_prefix:
                    logger.warning("CSRF token session binding mismatch")
                    return False

            return True

        except SignatureExpired:
            logger.warning("CSRF token expired")
            return False
        except BadSignature:
            logger.warning("Invalid CSRF token signature")
            return False
        except Exception as e:
            logger.error(f"CSRF token validation error: {e}")
            return False

    def is_exempt(self, request: Request) -> bool:
        """
        Check if a request is exempt from CSRF protection.

        Args:
            request: The incoming request

        Returns:
            True if request is exempt, False otherwise
        """
        # Check if path is in exempt list
        path = request.url.path
        for exempt_path in self.exempt_paths:
            if path.startswith(exempt_path):
                return True

        # Exempt safe methods (GET, HEAD, OPTIONS)
        if request.method not in self.protected_methods:
            return True

        # Exempt requests with API key authentication (if implemented)
        # This allows programmatic API access without CSRF tokens
        if request.headers.get('X-API-Key'):
            return True

        return False

    async def validate_request(self, request: Request) -> None:
        """
        Validate CSRF token for a request.

        Raises HTTPException if validation fails.

        Args:
            request: The incoming request
        """
        # Check if request is exempt
        if self.is_exempt(request):
            return

        # Extract CSRF token from header or form data
        csrf_token = request.headers.get('X-CSRF-Token')

        if not csrf_token:
            # Try to get from form data (for HTML forms)
            try:
                form = await request.form()
                csrf_token = form.get('csrf_token')
            except:
                pass

        if not csrf_token:
            # Try to get from JSON body
            try:
                body = await request.json()
                csrf_token = body.get('csrf_token')
            except:
                pass

        if not csrf_token:
            logger.warning(f"Missing CSRF token for {request.method} {request.url.path}")
            raise HTTPException(
                status_code=403,
                detail="CSRF token missing. Include X-CSRF-Token header or csrf_token in request body."
            )

        # Extract session token for binding validation
        session_token = request.cookies.get('session_token')
        if not session_token:
            auth_header = request.headers.get("Authorization")
            if auth_header and auth_header.startswith("Bearer "):
                session_token = auth_header.split(" ", 1)[1]

        # Validate token
        if not self.validate_token(csrf_token, session_token):
            logger.warning(
                f"Invalid CSRF token for {request.method} {request.url.path} "
                f"from {request.client.host if request.client else 'unknown'}"
            )
            raise HTTPException(
                status_code=403,
                detail="Invalid or expired CSRF token."
            )

    def get_token_from_session(self, request: Request) -> str:
        """
        Get CSRF token for current session.

        This can be called from route handlers to provide CSRF tokens to clients.

        Args:
            request: The incoming request

        Returns:
            CSRF token string
        """
        session_token = request.cookies.get('session_token')
        return self.generate_token(session_token)


# Global CSRF protection instance
csrf_protection = CSRFProtection()
