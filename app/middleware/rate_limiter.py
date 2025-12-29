"""Rate Limiting Middleware

Implements rate limiting to protect against brute force attacks, DoS,
and resource exhaustion on sensitive endpoints.
"""

from slowapi import Limiter
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from fastapi import Request, Response
from fastapi.responses import JSONResponse
import logging

logger = logging.getLogger(__name__)

# Create rate limiter instance
# Uses client IP address for rate limiting
limiter = Limiter(
    key_func=get_remote_address,
    default_limits=["200/minute"],  # Default: 200 requests per minute
    storage_uri="memory://",  # In-memory storage (can be changed to redis://)
)


async def rate_limit_exceeded_handler(request: Request, exc: RateLimitExceeded) -> Response:
    """
    Custom handler for rate limit exceeded errors.

    Returns a 429 Too Many Requests response with retry information.
    """
    logger.warning(
        f"Rate limit exceeded for {get_remote_address(request)} "
        f"on {request.method} {request.url.path}"
    )

    return JSONResponse(
        status_code=429,
        content={
            "error": "rate_limit_exceeded",
            "message": "Too many requests. Please try again later.",
            "retry_after": exc.detail.split("Retry after ")[1] if "Retry after" in exc.detail else "60 seconds"
        },
        headers={"Retry-After": "60"}
    )


# Rate limit configurations for different endpoint categories
RATE_LIMITS = {
    # Authentication endpoints - strict limits
    "auth_strict": "5/minute",  # Login attempts
    "auth_normal": "10/minute",  # Token validation, logout

    # API endpoints - moderate limits
    "api_read": "100/minute",  # GET requests
    "api_write": "50/minute",  # POST/PUT/DELETE requests

    # Admin endpoints - relaxed but monitored
    "admin": "30/minute",

    # Public endpoints - very strict
    "public": "20/minute",
}


def get_rate_limit(category: str) -> str:
    """Get rate limit string for a category."""
    return RATE_LIMITS.get(category, "100/minute")
