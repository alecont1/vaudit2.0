"""Authentication schemas for request/response models."""

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field


class LoginRequest(BaseModel):
    """Login request with credentials."""

    email: EmailStr
    password: str = Field(min_length=1)
    remember_me: bool = False


class TokenResponse(BaseModel):
    """JWT token response."""

    access_token: str
    token_type: str = "bearer"
    expires_in: int  # seconds until expiration


class PasswordChangeRequest(BaseModel):
    """Request to change password."""

    current_password: str
    new_password: str = Field(min_length=8)


class PasswordResetRequest(BaseModel):
    """Request to initiate password reset flow."""

    email: EmailStr


class PasswordResetConfirm(BaseModel):
    """Confirm password reset with token."""

    token: str
    new_password: str = Field(min_length=8)


class UserCreateAdmin(BaseModel):
    """Admin-only user creation schema.

    Password is auto-generated and sent via email.
    """

    email: EmailStr
    role: Literal["admin", "user"] = "user"


class UserUnlockRequest(BaseModel):
    """Request to unlock a locked user account."""

    email: EmailStr


class SessionInfo(BaseModel):
    """Information about an active session."""

    id: UUID
    device_info: str | None = None
    ip_address: str | None = None
    created_at: datetime
    expires_at: datetime
    is_current: bool = False
