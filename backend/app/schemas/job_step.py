"""Pydantic schema for job steps (per-tool orchestration records)."""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.models.enums import JobStepStatus


class JobStepRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    job_id: uuid.UUID
    sequence: int
    tool_key: str
    name: str
    required: bool
    status: JobStepStatus
    output: dict | None
    error: str | None
    started_at: datetime | None
    finished_at: datetime | None
    created_at: datetime
