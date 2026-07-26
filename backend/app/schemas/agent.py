"""Pydantic schemas for agents."""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class AgentCreate(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "name": "Vendor Analyzer",
                    "description": "Compares procurement vendors on security and pricing.",
                    "system_prompt": "You are a meticulous procurement research analyst.",
                    "model": "gemini-flash-latest",
                    "config": {"temperature": 0.2},
                    "is_active": True,
                }
            ]
        }
    )

    name: str = Field(min_length=1, max_length=255)
    description: str | None = None
    system_prompt: str | None = None
    model: str | None = Field(default=None, max_length=100)
    config: dict = Field(default_factory=dict)
    is_active: bool = True


class AgentUpdate(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={"examples": [{"description": "Now also compares SLAs.", "is_active": False}]}
    )

    name: str | None = Field(default=None, min_length=1, max_length=255)
    description: str | None = None
    system_prompt: str | None = None
    model: str | None = Field(default=None, max_length=100)
    config: dict | None = None
    is_active: bool | None = None


class AgentRead(BaseModel):
    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "examples": [
                {
                    "id": "a1b2c3d4-0000-4000-8000-000000000001",
                    "name": "Vendor Analyzer",
                    "description": "Compares procurement vendors on security and pricing.",
                    "system_prompt": "You are a meticulous procurement research analyst.",
                    "model": "gemini-flash-latest",
                    "config": {"temperature": 0.2},
                    "version": 1,
                    "is_active": True,
                    "created_by": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
                    "created_at": "2026-07-26T12:00:00Z",
                    "updated_at": "2026-07-26T12:00:00Z",
                }
            ]
        },
    )

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
