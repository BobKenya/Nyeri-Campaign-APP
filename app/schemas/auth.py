"""Pydantic schemas for authentication and user management."""

from datetime import datetime
from typing import Optional, List
from uuid import UUID
from pydantic import BaseModel, EmailStr, Field


# ── Auth ────────────────────────────────────────────────────────────

class LoginRequest(BaseModel):
    email: str
    password: str
    totp_code: Optional[str] = None


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int


class RefreshRequest(BaseModel):
    refresh_token: str


# ── User ────────────────────────────────────────────────────────────

class UserCreate(BaseModel):
    email: str
    full_name: str
    password: str = Field(min_length=8)
    role_id: UUID
    phone_number: Optional[str] = None


class UserUpdate(BaseModel):
    full_name: Optional[str] = None
    phone_number: Optional[str] = None
    is_active: Optional[bool] = None
    role_id: Optional[UUID] = None


class UserResponse(BaseModel):
    user_id: UUID
    email: str
    full_name: str
    role_id: UUID
    phone_number: Optional[str]
    is_active: bool
    two_factor_enabled: bool
    created_at: datetime
    last_login: Optional[datetime]

    class Config:
        from_attributes = True


# ── Role ────────────────────────────────────────────────────────────

class RoleCreate(BaseModel):
    role_name: str
    role_description: Optional[str] = None
    permissions_json: Optional[dict] = {}


class RoleResponse(BaseModel):
    role_id: UUID
    role_name: str
    role_description: Optional[str]
    permissions_json: dict

    class Config:
        from_attributes = True


# ── Notification ────────────────────────────────────────────────────

class NotificationResponse(BaseModel):
    notification_id: UUID
    type: str
    title: str
    body: Optional[str]
    read_at: Optional[datetime]
    created_at: datetime

    class Config:
        from_attributes = True
