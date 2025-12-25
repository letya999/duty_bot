"""
Pydantic schemas for request/response validation.

Provides type-safe models for all API endpoints with automatic validation,
documentation, and OpenAPI schema generation.
"""

from datetime import date, datetime
from typing import Optional

from pydantic import BaseModel, Field


# ============================================================================
# User Schemas
# ============================================================================


class UserBase(BaseModel):
    """Base user fields."""

    username: Optional[str] = Field(
        None,
        min_length=3,
        max_length=32,
        description="User login (3-32 alphanumeric characters)",
    )
    email: Optional[str] = Field(None, description="User email address")
    first_name: Optional[str] = Field(
        None, max_length=50, description="User first name"
    )
    last_name: Optional[str] = Field(None, max_length=50, description="User last name")
    display_name: Optional[str] = Field(
        None, max_length=100, description="User display name"
    )


class UserCreate(UserBase):
    """Create user request."""

    workspace_id: int = Field(..., gt=0, description="Workspace ID")
    telegram_username: Optional[str] = Field(
        None, description="Telegram username (@username)"
    )
    slack_user_id: Optional[str] = Field(None, description="Slack user ID")


class UserUpdate(UserBase):
    """Update user request."""

    is_admin: Optional[bool] = Field(None, description="Admin status")


class UserResponse(UserBase):
    """User response model."""

    id: int = Field(..., description="User ID")
    workspace_id: int = Field(..., description="Workspace ID")
    is_admin: bool = Field(..., description="Is admin user")
    telegram_id: Optional[int] = Field(None, description="Telegram user ID")
    telegram_username: Optional[str] = Field(None, description="Telegram username")
    slack_user_id: Optional[str] = Field(None, description="Slack user ID")
    created_at: datetime = Field(..., description="Created timestamp")

    class Config:
        from_attributes = True


# ============================================================================
# Team Schemas
# ============================================================================


class TeamBase(BaseModel):
    """Base team fields."""

    name: str = Field(
        ..., min_length=1, max_length=100, description="Team name (unique per workspace)"
    )
    display_name: str = Field(
        ..., min_length=1, max_length=100, description="Team display name"
    )
    has_shifts: bool = Field(
        False, description="Whether this team uses shift scheduling"
    )


class TeamCreate(TeamBase):
    """Create team request."""

    workspace_id: int = Field(..., gt=0, description="Workspace ID")
    team_lead_id: Optional[int] = Field(None, gt=0, description="Team lead user ID")


class TeamUpdate(BaseModel):
    """Update team request."""

    display_name: Optional[str] = Field(
        None, min_length=1, max_length=100, description="Team display name"
    )
    has_shifts: Optional[bool] = Field(
        None, description="Whether this team uses shift scheduling"
    )
    team_lead_id: Optional[int] = Field(None, gt=0, description="Team lead user ID")


class TeamResponse(TeamBase):
    """Team response model."""

    id: int = Field(..., description="Team ID")
    workspace_id: int = Field(..., description="Workspace ID")
    team_lead_id: Optional[int] = Field(None, description="Team lead user ID")
    created_at: datetime = Field(..., description="Created timestamp")

    class Config:
        from_attributes = True


class TeamDetailResponse(TeamResponse):
    """Team with members detail response."""

    members: list[UserResponse] = Field(default_factory=list, description="Team members")


# ============================================================================
# Schedule Schemas
# ============================================================================


class ScheduleBase(BaseModel):
    """Base schedule fields."""

    duty_date: date = Field(..., description="Duty date")
    user_id: Optional[int] = Field(None, gt=0, description="Assigned user ID")


class ScheduleCreate(ScheduleBase):
    """Create schedule request."""

    team_id: int = Field(..., gt=0, description="Team ID")


class ScheduleUpdate(BaseModel):
    """Update schedule request."""

    user_id: Optional[int] = Field(None, gt=0, description="Assigned user ID")


class ScheduleResponse(ScheduleBase):
    """Schedule response model."""

    id: int = Field(..., description="Schedule ID")
    team_id: int = Field(..., description="Team ID")
    created_at: datetime = Field(..., description="Created timestamp")

    class Config:
        from_attributes = True


# ============================================================================
# Shift Schemas
# ============================================================================


class ShiftBase(BaseModel):
    """Base shift fields."""

    shift_date: date = Field(..., description="Shift date")


class ShiftCreate(ShiftBase):
    """Create shift request."""

    team_id: int = Field(..., gt=0, description="Team ID")
    user_ids: list[int] = Field(
        ...,
        min_items=1,
        description="List of user IDs assigned to this shift",
    )


class ShiftUpdate(BaseModel):
    """Update shift request."""

    user_ids: Optional[list[int]] = Field(
        None, min_items=1, description="List of user IDs assigned to this shift"
    )


class ShiftResponse(ShiftBase):
    """Shift response model."""

    id: int = Field(..., description="Shift ID")
    team_id: int = Field(..., description="Team ID")
    created_at: datetime = Field(..., description="Created timestamp")

    class Config:
        from_attributes = True


class ShiftDetailResponse(ShiftResponse):
    """Shift with assigned users response."""

    users: list[UserResponse] = Field(default_factory=list, description="Assigned users")


# ============================================================================
# Escalation Schemas
# ============================================================================


class EscalationCreate(BaseModel):
    """Create escalation request."""

    team_id: Optional[int] = Field(None, gt=0, description="Team ID (NULL for global)")
    cto_id: Optional[int] = Field(None, gt=0, description="CTO user ID")


class EscalationUpdate(BaseModel):
    """Update escalation request."""

    cto_id: Optional[int] = Field(None, gt=0, description="CTO user ID")


class EscalationResponse(BaseModel):
    """Escalation response model."""

    id: int = Field(..., description="Escalation ID")
    team_id: Optional[int] = Field(None, description="Team ID")
    cto_id: Optional[int] = Field(None, description="CTO user ID")
    created_at: datetime = Field(..., description="Created timestamp")

    class Config:
        from_attributes = True


# ============================================================================
# Workspace Schemas
# ============================================================================


class WorkspaceCreate(BaseModel):
    """Create workspace request."""

    name: str = Field(
        ..., min_length=1, max_length=255, description="Workspace display name"
    )
    workspace_type: str = Field(
        ..., description="Workspace type ('telegram' or 'slack')"
    )
    external_id: str = Field(
        ...,
        min_length=1,
        max_length=255,
        description="External workspace ID (chat_id for Telegram, workspace_id for Slack)",
    )


class WorkspaceResponse(BaseModel):
    """Workspace response model."""

    id: int = Field(..., description="Workspace ID")
    name: str = Field(..., description="Workspace name")
    workspace_type: str = Field(..., description="Workspace type")
    external_id: str = Field(..., description="External workspace ID")
    created_at: datetime = Field(..., description="Created timestamp")

    class Config:
        from_attributes = True


# ============================================================================
# Rotation Config Schemas
# ============================================================================


class RotationConfigCreate(BaseModel):
    """Create rotation config request."""

    team_id: int = Field(..., gt=0, description="Team ID")
    enabled: bool = Field(False, description="Enable automatic rotation")
    member_ids: list[int] = Field(
        ..., min_items=1, description="Ordered list of user IDs for rotation"
    )
    skip_unavailable: bool = Field(
        False, description="Skip unavailable users (for future use)"
    )


class RotationConfigUpdate(BaseModel):
    """Update rotation config request."""

    enabled: Optional[bool] = Field(None, description="Enable automatic rotation")
    member_ids: Optional[list[int]] = Field(
        None, min_items=1, description="Ordered list of user IDs for rotation"
    )
    skip_unavailable: Optional[bool] = Field(
        None, description="Skip unavailable users"
    )


class RotationConfigResponse(BaseModel):
    """Rotation config response model."""

    id: int = Field(..., description="Config ID")
    team_id: int = Field(..., description="Team ID")
    enabled: bool = Field(..., description="Is rotation enabled")
    member_ids: list[int] = Field(..., description="User IDs in rotation order")
    last_assigned_user_id: Optional[int] = Field(
        None, description="Last assigned user ID"
    )
    last_assigned_date: Optional[date] = Field(None, description="Last assignment date")
    skip_unavailable: bool = Field(..., description="Skip unavailable users")
    created_at: datetime = Field(..., description="Created timestamp")
    updated_at: datetime = Field(..., description="Updated timestamp")

    class Config:
        from_attributes = True


# ============================================================================
# Stats Schemas
# ============================================================================


class StatsResponse(BaseModel):
    """User statistics response model."""

    user_id: int = Field(..., description="User ID")
    team_id: int = Field(..., description="Team ID")
    year: int = Field(..., description="Year")
    month: int = Field(..., ge=1, le=12, description="Month (1-12)")
    duty_days: int = Field(default=0, description="Number of duty days")
    shift_days: int = Field(default=0, description="Number of shift days")
    hours_worked: Optional[int] = Field(None, description="Hours worked")


# ============================================================================
# Admin Log Schemas
# ============================================================================


class AdminLogResponse(BaseModel):
    """Admin action log response model."""

    id: int = Field(..., description="Log entry ID")
    workspace_id: int = Field(..., description="Workspace ID")
    admin_user_id: int = Field(..., description="Admin user ID")
    action: str = Field(..., description="Action performed")
    target_user_id: Optional[int] = Field(None, description="Target user ID")
    timestamp: datetime = Field(..., description="Action timestamp")
    details: Optional[str] = Field(None, description="Additional details (JSON)")

    class Config:
        from_attributes = True


# ============================================================================
# Generic Response Schemas
# ============================================================================


class ErrorResponse(BaseModel):
    """Standard error response."""

    error_code: str = Field(..., description="Error code")
    message: str = Field(..., description="Error message")
    status_code: int = Field(..., description="HTTP status code")
    details: Optional[dict] = Field(None, description="Additional error details")


class SuccessResponse(BaseModel):
    """Generic success response wrapper."""

    success: bool = Field(True, description="Operation success status")
    message: Optional[str] = Field(None, description="Optional message")
    data: Optional[dict] = Field(None, description="Response data")


class PaginatedResponse(BaseModel):
    """Paginated response wrapper."""

    items: list = Field(..., description="Result items")
    total: int = Field(..., description="Total items count")
    page: int = Field(..., ge=1, description="Current page")
    page_size: int = Field(..., ge=1, description="Items per page")
    total_pages: int = Field(..., ge=0, description="Total number of pages")
