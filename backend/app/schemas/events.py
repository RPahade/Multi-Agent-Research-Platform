"""Event schema for Kafka messages published to ``agent.job.events``."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from pydantic import BaseModel, Field


def _now() -> datetime:
    return datetime.now(timezone.utc)


class JobEvent(BaseModel):
    """A job lifecycle event. Required fields per the milestone: job_id, status, timestamp."""

    event_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    event_type: str = "job.event"  # e.g. job.created / job.running / job.progress / job.succeeded
    job_id: str
    status: str
    progress: int | None = None
    current_step: str | None = None
    timestamp: datetime = Field(default_factory=_now)
