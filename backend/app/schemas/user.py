"""Pydantic schemas for users."""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from app.models.enums import UserRole


class UserCreate(BaseModel):
    """Payload for creating a user (admin-only endpoint)."""

    email: EmailStr
    # bcrypt only uses the first 72 bytes; cap length to avoid silent truncation.
    password: str = Field(min_length=8, max_length=72)
    full_name: str | None = Field(default=None, max_length=255)
    role: UserRole = UserRole.ANALYST


class UserUpdate(BaseModel):
    """Partial update for a user (admin-only). Only provided fields change."""

    full_name: str | None = Field(default=None, max_length=255)
    role: UserRole | None = None
    is_active: bool | None = None
    password: str | None = Field(default=None, min_length=8, max_length=72)


class UserRead(BaseModel):
    """Public representation of a user."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    email: EmailStr
    full_name: str | None
    role: UserRole
    is_active: bool
    created_at: datetime
