"""Pydantic response schemas for health endpoints."""

from __future__ import annotations

from pydantic import BaseModel


class HealthResponse(BaseModel):
    """Liveness response payload."""

    status: str
    app: str
    version: str
    env: str


class DBHealthResponse(BaseModel):
    """Readiness response payload (database connectivity)."""

    status: str
    database: str
