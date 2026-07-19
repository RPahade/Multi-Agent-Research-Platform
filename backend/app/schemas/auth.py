"""Pydantic schemas for authentication flows."""

from __future__ import annotations

from pydantic import BaseModel


class TokenPair(BaseModel):
    """Access + refresh token response."""

    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class RefreshRequest(BaseModel):
    """Body carrying a refresh token (for /refresh and /logout)."""

    refresh_token: str


class MessageResponse(BaseModel):
    """Simple message envelope."""

    detail: str
