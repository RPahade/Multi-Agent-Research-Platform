"""Pydantic schemas for tools."""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import ToolCategory


class ToolCreate(BaseModel):
    key: str = Field(min_length=1, max_length=100, description="Stable machine key")
    name: str = Field(min_length=1, max_length=255)
    description: str | None = None
    category: ToolCategory
    config: dict = Field(default_factory=dict)
    enabled: bool = True


class ToolUpdate(BaseModel):
    # ``key`` is immutable once created.
    name: str | None = Field(default=None, min_length=1, max_length=255)
    description: str | None = None
    category: ToolCategory | None = None
    config: dict | None = None
    enabled: bool | None = None


class ToolRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

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
