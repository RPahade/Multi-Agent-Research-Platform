"""Pydantic schemas for jobs."""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.core.config import settings
from app.models.enums import JobStatus, JobType


class JobCreate(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "type": "research",
                    "input": {
                        "query": "Compare Vendor A and Vendor B on data residency and pricing",
                        "document_ids": ["d4e5f6a7-0000-4000-8000-000000000004"],
                        "top_k": 8,
                    },
                }
            ]
        }
    )

    type: JobType = JobType.RESEARCH
    # Free-form run parameters. For a research job: query, document_ids, top_k, or inline sources.
    # For the simulated runner: steps (int), step_seconds (float), fail (bool), fail_times (int), fail_step (int).
    input: dict = Field(default_factory=dict)
    agent_id: uuid.UUID | None = None
    max_attempts: int = Field(default=settings.default_max_attempts, ge=1, le=10)


class JobRead(BaseModel):
    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "examples": [
                {
                    "id": "f6a7b8c9-0000-4000-8000-000000000006",
                    "user_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
                    "agent_id": None,
                    "type": "research",
                    "status": "running",
                    "input": {"query": "Compare Vendor A and Vendor B", "top_k": 8},
                    "progress": 60,
                    "current_step": "Synthesizing report",
                    "error": None,
                    "idempotency_key": None,
                    "attempts": 1,
                    "max_attempts": 3,
                    "last_heartbeat": "2026-07-26T12:00:05Z",
                    "started_at": "2026-07-26T12:00:00Z",
                    "finished_at": None,
                    "created_at": "2026-07-26T12:00:00Z",
                    "updated_at": "2026-07-26T12:00:05Z",
                }
            ]
        },
    )

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
