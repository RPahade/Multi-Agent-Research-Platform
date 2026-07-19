"""Pydantic schemas for agents."""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class AgentCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    description: str | None = None
    system_prompt: str | None = None
    model: str | None = Field(default=None, max_length=100)
    config: dict = Field(default_factory=dict)
    is_active: bool = True


class AgentUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    description: str | None = None
    system_prompt: str | None = None
    model: str | None = Field(default=None, max_length=100)
    config: dict | None = None
    is_active: bool | None = None


class AgentRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    description: str | None
    system_prompt: str | None
    model: str | None
    config: dict
    version: int
    is_active: bool
    created_by: uuid.UUID | None
    created_at: datetime
    updated_at: datetime
