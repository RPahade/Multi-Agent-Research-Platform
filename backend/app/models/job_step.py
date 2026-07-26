"""JobStep model — one row per tool executed within an orchestrated job.

Gives per-tool status/output/error visibility (partial-failure reporting) and lays
the groundwork for tracing.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, Integer, String, Text, UniqueConstraint, text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, UUIDPrimaryKeyMixin
from app.models.enums import JobStepStatus


class JobStep(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "job_steps"
    __table_args__ = (UniqueConstraint("job_id", "sequence", name="uq_job_step_sequence"),)

    job_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("jobs.id", ondelete="CASCADE"), nullable=False, index=True
    )
    sequence: Mapped[int] = mapped_column(Integer, nullable=False)
    tool_key: Mapped[str] = mapped_column(String(100), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    required: Mapped[bool] = mapped_column(nullable=False, server_default=text("true"))
    status: Mapped[JobStepStatus] = mapped_column(
        Enum(JobStepStatus, name="job_step_status", values_callable=lambda e: [m.value for m in e]),
        nullable=False,
        server_default=JobStepStatus.PENDING.value,
    )
    output: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=text("now()"), nullable=False
    )

    def __repr__(self) -> str:  # pragma: no cover
        return f"<JobStep {self.sequence}:{self.tool_key} status={self.status}>"
