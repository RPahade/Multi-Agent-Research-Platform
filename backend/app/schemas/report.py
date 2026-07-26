"""Pydantic schemas for reports and report versions."""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import ReportStatus

_CONTENT_EXAMPLE = {
    "title": "Vendor A vs Vendor B — Data Residency & Pricing",
    "summary": "Vendor B stores data in the EU; Vendor A is US-only. Vendor B is cheaper.",
    "sections": [
        {"heading": "Data Residency", "body": "Vendor B stores data in Frankfurt and Dublin [1]. Vendor A is US-only [2]."}
    ],
    "citations": [{"claim": "Vendor B stores data in the EU.", "source": "[1]"}],
}


class ReportCreate(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {"title": "Vendor A vs Vendor B", "summary": "Executive comparison.",
                 "content": _CONTENT_EXAMPLE, "status": "draft"}
            ]
        }
    )

    title: str = Field(min_length=1, max_length=500)
    summary: str | None = None
    content: dict = Field(default_factory=dict)
    status: ReportStatus = ReportStatus.DRAFT
    job_id: uuid.UUID | None = None


class ReportUpdate(BaseModel):
    model_config = ConfigDict(json_schema_extra={"examples": [{"status": "final", "content": _CONTENT_EXAMPLE}]})

    title: str | None = Field(default=None, min_length=1, max_length=500)
    summary: str | None = None
    content: dict | None = None
    status: ReportStatus | None = None


class ReportRead(BaseModel):
    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "examples": [
                {
                    "id": "c3d4e5f6-0000-4000-8000-000000000003",
                    "job_id": "d4e5f6a7-0000-4000-8000-000000000004",
                    "title": "Vendor A vs Vendor B",
                    "summary": "Executive comparison.",
                    "content": _CONTENT_EXAMPLE,
                    "status": "final",
                    "version": 2,
                    "created_by": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
                    "created_at": "2026-07-26T12:00:00Z",
                    "updated_at": "2026-07-26T12:05:00Z",
                }
            ]
        },
    )

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
    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "examples": [
                {
                    "id": "e5f6a7b8-0000-4000-8000-000000000005",
                    "report_id": "c3d4e5f6-0000-4000-8000-000000000003",
                    "version": 1,
                    "title": "Vendor A vs Vendor B",
                    "summary": "First draft.",
                    "content": _CONTENT_EXAMPLE,
                    "created_by": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
                    "created_at": "2026-07-26T12:00:00Z",
                }
            ]
        },
    )

    id: uuid.UUID
    report_id: uuid.UUID
    version: int
    title: str
    summary: str | None
    content: dict
    created_by: uuid.UUID | None
    created_at: datetime
