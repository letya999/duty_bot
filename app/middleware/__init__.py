"""Middleware components for the application."""

from .security_headers import SecurityHeadersMiddleware

__all__ = ['SecurityHeadersMiddleware']
