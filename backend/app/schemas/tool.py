"""Pydantic schemas for tools."""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import ToolCategory


class ToolCreate(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "key": "web_research",
                    "name": "Web Research",
                    "description": "Searches external sources for a query.",
                    "category": "web_research",
                    "config": {"max_results": 5},
                    "enabled": True,
                }
            ]
        }
    )

    key: str = Field(min_length=1, max_length=100, description="Stable machine key")
    name: str = Field(min_length=1, max_length=255)
    description: str | None = None
    category: ToolCategory
    config: dict = Field(default_factory=dict)
    enabled: bool = True


class ToolUpdate(BaseModel):
    # ``key`` is immutable once created.
    model_config = ConfigDict(json_schema_extra={"examples": [{"enabled": False, "config": {"max_results": 10}}]})

    name: str | None = Field(default=None, min_length=1, max_length=255)
    description: str | None = None
    category: ToolCategory | None = None
    config: dict | None = None
    enabled: bool | None = None


class ToolRead(BaseModel):
    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "examples": [
                {
                    "id": "b2c3d4e5-0000-4000-8000-000000000002",
                    "key": "web_research",
                    "name": "Web Research",
                    "description": "Searches external sources for a query.",
                    "category": "web_research",
                    "config": {"max_results": 5},
                    "enabled": True,
                    "version": 1,
                    "created_at": "2026-07-26T12:00:00Z",
                    "updated_at": "2026-07-26T12:00:00Z",
                }
            ]
        },
    )

    id: uuid.UUID
    key: str
    name: str
    description: str | None
    category: ToolCategory
    config: dict
    enabled: bool
    version: int
    created_at: datetime
    updated_at: datetime
