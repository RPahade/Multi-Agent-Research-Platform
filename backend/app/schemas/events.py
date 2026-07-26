"""Event schema for Kafka messages published to ``agent.job.events``."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from pydantic import BaseModel, ConfigDict, Field


def _now() -> datetime:
    return datetime.now(timezone.utc)


class JobEvent(BaseModel):
    """A job lifecycle event. Required fields per the milestone: job_id, status, timestamp."""

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "event_id": "9f1c2a7e-0000-4000-8000-00000000000a",
                    "event_type": "job.progress",
                    "job_id": "f6a7b8c9-0000-4000-8000-000000000006",
                    "status": "running",
                    "progress": 60,
                    "current_step": "Synthesizing report",
                    "timestamp": "2026-07-26T12:00:05Z",
                }
            ]
        }
    )

    event_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    event_type: str = "job.event"  # e.g. job.created / job.running / job.progress / job.succeeded
    job_id: str
    status: str
    progress: int | None = None
    current_step: str | None = None
    timestamp: datetime = Field(default_factory=_now)
