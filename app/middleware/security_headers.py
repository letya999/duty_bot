"""Security Headers Middleware

Adds essential security headers to all HTTP responses to protect against
common web vulnerabilities like clickjacking, MIME sniffing, and XSS attacks.
"""

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """
    Middleware that adds security headers to all responses.

    Security Headers Added:
    - X-Content-Type-Options: nosniff
      Prevents MIME type sniffing, reducing exposure to drive-by download attacks

    - X-Frame-Options: DENY
      Prevents clickjacking by not allowing the page to be loaded in a frame

    - X-XSS-Protection: 1; mode=block
      Enables XSS filtering in older browsers (defense in depth)

    - Strict-Transport-Security: max-age=31536000; includeSubDomains
      Forces HTTPS connections for one year, including all subdomains

    - Content-Security-Policy: default-src 'self'
      Restricts resource loading to same origin by default

    - Referrer-Policy: strict-origin-when-cross-origin
      Controls referrer information sent with requests
    """

    async def dispatch(self, request: Request, call_next) -> Response:
        """
        Process the request and add security headers to the response.

        Args:
            request: The incoming HTTP request
            call_next: The next middleware or route handler

        Returns:
            Response with added security headers
        """
        response = await call_next(request)

        # Prevent MIME type sniffing
        response.headers["X-Content-Type-Options"] = "nosniff"

        # Prevent clickjacking attacks
        response.headers["X-Frame-Options"] = "DENY"

        # Enable XSS protection (legacy browsers)
        response.headers["X-XSS-Protection"] = "1; mode=block"

        # Force HTTPS for 1 year (only add if request is HTTPS)
        # In production behind a reverse proxy, check X-Forwarded-Proto header
        is_https = (
            request.url.scheme == "https" or
            request.headers.get("X-Forwarded-Proto") == "https"
        )
        if is_https:
            response.headers["Strict-Transport-Security"] = (
                "max-age=31536000; includeSubDomains"
            )

        # Content Security Policy - restrict resource loading
        # Note: This is a basic policy. Adjust based on your application needs.
        # For applications with inline scripts/styles, you'll need to adjust this.
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; "
            "script-src 'self' 'unsafe-inline' 'unsafe-eval' https://telegram.org https://oauth.telegram.org; "
            "style-src 'self' 'unsafe-inline'; "
            "img-src 'self' data: https:; "
            "font-src 'self' data:; "
            "connect-src 'self' https://api.telegram.org; "
            "frame-ancestors 'none'"
        )

        # Control referrer information
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"

        # Prevent browser features that could be exploited
        response.headers["Permissions-Policy"] = (
            "geolocation=(), microphone=(), camera=()"
        )

        return response
