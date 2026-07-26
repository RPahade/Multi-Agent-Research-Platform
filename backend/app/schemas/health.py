"""Pydantic response schemas for health endpoints."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict


class HealthResponse(BaseModel):
    """Liveness response payload."""

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "status": "ok",
                    "app": "Multi-Agent Research Intelligence Platform",
                    "version": "0.1.0",
                    "env": "development",
                }
            ]
        }
    )

    status: str
    app: str
    version: str
    env: str


class DBHealthResponse(BaseModel):
    """Readiness response payload (database connectivity)."""

    model_config = ConfigDict(json_schema_extra={"examples": [{"status": "ok", "database": "reachable"}]})

    status: str
    database: str
