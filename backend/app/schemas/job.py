"""Pydantic schemas for jobs."""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.core.config import settings
from app.models.enums import JobStatus, JobType


class JobCreate(BaseModel):
    type: JobType = JobType.RESEARCH
    # Free-form run parameters. For the current simulated runner:
    #   steps (int), step_seconds (float), fail (bool), fail_times (int), fail_step (int)
    input: dict = Field(default_factory=dict)
    agent_id: uuid.UUID | None = None
    max_attempts: int = Field(default=settings.default_max_attempts, ge=1, le=10)


class JobRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    user_id: uuid.UUID | None
    agent_id: uuid.UUID | None
    type: JobType
    status: JobStatus
    input: dict
    progress: int
    current_step: str | None
    error: str | None
    idempotency_key: str | None
    attempts: int
    max_attempts: int
    last_heartbeat: datetime | None
    started_at: datetime | None
    finished_at: datetime | None
    created_at: datetime
    updated_at: datetime
