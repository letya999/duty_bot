"""
Decorators for common functionality and cross-cutting concerns.
"""

import functools
from typing import Any, Callable, TypeVar, cast

from sqlalchemy.ext.asyncio import AsyncSession

from app.exceptions import NotFoundError
from app.repositories.workspace_repository import WorkspaceRepository

F = TypeVar("F", bound=Callable[..., Any])


def with_workspace_context(fn: F) -> F:
    """
    Decorator that ensures workspace context is available.

    Extracts workspace_id from function kwargs and validates it exists.
    Adds workspace object to kwargs['workspace'].

    Usage:
        @with_workspace_context
        async def process_data(user_id: int, workspace_id: int, workspace: Workspace = None):
            ...
    """

    @functools.wraps(fn)
    async def wrapper(*args: Any, db: AsyncSession, **kwargs: Any) -> Any:
        workspace_id = kwargs.get("workspace_id")
        if not workspace_id:
            raise ValueError("workspace_id is required in function arguments")

        workspace_repo = WorkspaceRepository(db)
        workspace = await workspace_repo.get_by_id(workspace_id)

        if not workspace:
            raise NotFoundError("Workspace", f"Workspace {workspace_id} not found")

        kwargs["workspace"] = workspace
        return await fn(*args, db=db, **kwargs)

    return cast(F, wrapper)


def validate_input(**validators: Callable[[Any], bool]) -> Callable[[F], F]:
    """
    Decorator for input validation.

    Usage:
        @validate_input(user_id=lambda x: x > 0, email=lambda x: "@" in x)
        async def create_user(user_id: int, email: str):
            ...
    """

    def decorator(fn: F) -> F:
        @functools.wraps(fn)
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            from app.exceptions import ValidationError

            for key, validator in validators.items():
                if key in kwargs:
                    if not validator(kwargs[key]):
                        raise ValidationError(f"Invalid value for {key}")

            return await fn(*args, **kwargs)

        return cast(F, wrapper)

    return decorator


def require_admin(fn: F) -> F:
    """
    Decorator that checks if user has admin permissions.

    Requires 'user' and 'workspace_id' in function kwargs.
    """

    @functools.wraps(fn)
    async def wrapper(*args: Any, user: Any = None, **kwargs: Any) -> Any:
        from app.exceptions import AuthorizationError

        if not user or not user.is_admin:
            raise AuthorizationError("Admin access required")

        return await fn(*args, user=user, **kwargs)

    return cast(F, wrapper)


def require_workspace_membership(fn: F) -> F:
    """
    Decorator that validates user belongs to workspace.

    Requires 'user', 'workspace_id' in function kwargs.
    """

    @functools.wraps(fn)
    async def wrapper(*args: Any, user: Any = None, **kwargs: Any) -> Any:
        from app.exceptions import AuthorizationError

        workspace_id = kwargs.get("workspace_id")
        if not user or user.workspace_id != workspace_id:
            raise AuthorizationError("User does not belong to this workspace")

        return await fn(*args, user=user, **kwargs)

    return cast(F, wrapper)
