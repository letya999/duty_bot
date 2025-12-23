"""Retry utilities for handling transient database connection errors"""
import asyncio
import logging
from typing import Callable, TypeVar, Any
from sqlalchemy.exc import OperationalError, InterfaceError, DBAPIError
import asyncpg

logger = logging.getLogger(__name__)

T = TypeVar('T')

# Errors that indicate a connection issue and should trigger a retry
RETRYABLE_ERRORS = (
    asyncpg.exceptions._base.InterfaceError,
    OperationalError,
    InterfaceError,
    DBAPIError,
)


async def retry_on_connection_error(
    func: Callable[..., Any],
    *args,
    max_retries: int = 3,
    initial_delay: float = 0.1,
    backoff_factor: float = 2.0,
    **kwargs
) -> Any:
    """
    Retry a function if it fails with a connection error.

    Args:
        func: The async function to call
        *args: Positional arguments for func
        max_retries: Maximum number of retries
        initial_delay: Initial delay in seconds before first retry
        backoff_factor: Multiply delay by this factor for each retry
        **kwargs: Keyword arguments for func

    Returns:
        The result of func() if successful

    Raises:
        The last exception if all retries fail
    """
    delay = initial_delay
    last_exception = None

    for attempt in range(max_retries + 1):
        try:
            return await func(*args, **kwargs)
        except Exception as e:
            last_exception = e

            # Check if this is a retryable error
            is_connection_error = False
            if isinstance(e, RETRYABLE_ERRORS):
                is_connection_error = True
            # Also check for connection closed string in error message
            elif "connection is closed" in str(e).lower() or "connection refused" in str(e).lower():
                is_connection_error = True

            if is_connection_error and attempt < max_retries:
                logger.warning(
                    f"Connection error on attempt {attempt + 1}/{max_retries + 1}: {e}. "
                    f"Retrying in {delay}s..."
                )
                await asyncio.sleep(delay)
                delay *= backoff_factor
            else:
                # Not a connection error or no retries left
                raise


async def with_retry(
    func: Callable[..., Any],
    *args,
    max_retries: int = 3,
    initial_delay: float = 0.1,
    backoff_factor: float = 2.0,
    **kwargs
) -> Any:
    """
    Decorator-like wrapper to retry a function on connection errors.

    Usage:
        result = await with_retry(some_async_func, arg1, arg2, kwarg1=value1)
    """
    return await retry_on_connection_error(
        func,
        *args,
        max_retries=max_retries,
        initial_delay=initial_delay,
        backoff_factor=backoff_factor,
        **kwargs
    )
