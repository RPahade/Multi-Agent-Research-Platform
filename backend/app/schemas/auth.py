"""Pydantic schemas for authentication flows."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict


class TokenPair(BaseModel):
    """Access + refresh token response."""

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIzZmE4NWY2NC01NzE3Iiwicm9sZSI6ImFuYWx5c3QiLCJ0eXBlIjoiYWNjZXNzIn0.signature",
                    "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIzZmE4NWY2NC01NzE3IiwidHlwZSI6InJlZnJlc2gifQ.signature",
                    "token_type": "bearer",
                }
            ]
        }
    )

    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class RefreshRequest(BaseModel):
    """Body carrying a refresh token (for /refresh and /logout)."""

    model_config = ConfigDict(
        json_schema_extra={"examples": [{"refresh_token": "eyJhbGciOiJIUzI1NiJ9.eyJ0eXBlIjoicmVmcmVzaCJ9.signature"}]}
    )

    refresh_token: str


class MessageResponse(BaseModel):
    """Simple message envelope."""

    model_config = ConfigDict(json_schema_extra={"examples": [{"detail": "Logged out"}]})

    detail: str
