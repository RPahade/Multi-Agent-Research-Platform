"""Pydantic schemas for users."""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from app.models.enums import UserRole


class UserCreate(BaseModel):
    """Payload for creating a user (admin-only endpoint)."""

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {"email": "analyst@acme.com", "password": "Passw0rd1", "full_name": "Ann Analyst", "role": "analyst"}
            ]
        }
    )

    email: EmailStr
    # bcrypt only uses the first 72 bytes; cap length to avoid silent truncation.
    password: str = Field(min_length=8, max_length=72)
    full_name: str | None = Field(default=None, max_length=255)
    role: UserRole = UserRole.ANALYST


class UserUpdate(BaseModel):
    """Partial update for a user (admin-only). Only provided fields change."""

    model_config = ConfigDict(json_schema_extra={"examples": [{"full_name": "Ann A. Analyst", "is_active": False}]})

    full_name: str | None = Field(default=None, max_length=255)
    role: UserRole | None = None
    is_active: bool | None = None
    password: str | None = Field(default=None, min_length=8, max_length=72)


class UserRead(BaseModel):
    """Public representation of a user."""

    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "examples": [
                {
                    "id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
                    "email": "analyst@acme.com",
                    "full_name": "Ann Analyst",
                    "role": "analyst",
                    "is_active": True,
                    "created_at": "2026-07-26T12:00:00Z",
                }
            ]
        },
    )

    id: uuid.UUID
    email: EmailStr
    full_name: str | None
    role: UserRole
    is_active: bool
    created_at: datetime
