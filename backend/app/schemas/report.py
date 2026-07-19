"""Pydantic schemas for reports and report versions."""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import ReportStatus


class ReportCreate(BaseModel):
    title: str = Field(min_length=1, max_length=500)
    summary: str | None = None
    content: dict = Field(default_factory=dict)
    status: ReportStatus = ReportStatus.DRAFT
    job_id: uuid.UUID | None = None


class ReportUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=500)
    summary: str | None = None
    content: dict | None = None
    status: ReportStatus | None = None


class ReportRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    job_id: uuid.UUID | None
    title: str
    summary: str | None
    content: dict
    status: ReportStatus
    version: int
    created_by: uuid.UUID | None
    created_at: datetime
    updated_at: datetime


class ReportVersionRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    report_id: uuid.UUID
    version: int
    title: str
    summary: str | None
    content: dict
    created_by: uuid.UUID | None
    created_at: datetime
