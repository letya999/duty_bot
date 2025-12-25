"""
Custom application exceptions for structured error handling.
"""

from typing import Any, Optional


class ApplicationException(Exception):
    """Base exception for all application errors."""

    def __init__(
        self,
        message: str,
        status_code: int = 500,
        error_code: str = "INTERNAL_ERROR",
        details: Optional[dict[str, Any]] = None,
    ):
        self.message = message
        self.status_code = status_code
        self.error_code = error_code
        self.details = details or {}
        super().__init__(self.message)


class ValidationError(ApplicationException):
    """Raised when input validation fails."""

    def __init__(self, message: str, details: Optional[dict[str, Any]] = None):
        super().__init__(
            message=message,
            status_code=400,
            error_code="VALIDATION_ERROR",
            details=details,
        )


class AuthenticationError(ApplicationException):
    """Raised when authentication fails."""

    def __init__(self, message: str = "Authentication failed"):
        super().__init__(
            message=message,
            status_code=401,
            error_code="AUTHENTICATION_ERROR",
        )


class AuthorizationError(ApplicationException):
    """Raised when user lacks required permissions."""

    def __init__(self, message: str = "Access denied"):
        super().__init__(
            message=message,
            status_code=403,
            error_code="AUTHORIZATION_ERROR",
        )


class NotFoundError(ApplicationException):
    """Raised when a resource is not found."""

    def __init__(self, resource: str, message: Optional[str] = None):
        if message is None:
            message = f"{resource} not found"
        super().__init__(
            message=message,
            status_code=404,
            error_code="NOT_FOUND_ERROR",
            details={"resource": resource},
        )


class ConflictError(ApplicationException):
    """Raised when there is a resource conflict."""

    def __init__(self, message: str, details: Optional[dict[str, Any]] = None):
        super().__init__(
            message=message,
            status_code=409,
            error_code="CONFLICT_ERROR",
            details=details,
        )


class CommandError(ApplicationException):
    """Raised when command parsing or execution fails."""

    def __init__(self, message: str, details: Optional[dict[str, Any]] = None):
        super().__init__(
            message=message,
            status_code=400,
            error_code="COMMAND_ERROR",
            details=details,
        )
