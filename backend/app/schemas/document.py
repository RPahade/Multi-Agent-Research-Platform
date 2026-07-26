"""Pydantic schemas for documents and their chunks."""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.models.enums import DocumentStatus

_DOC_EXAMPLE = {
    "id": "d4e5f6a7-0000-4000-8000-000000000004",
    "filename": "vendor_a_proposal.pdf",
    "title": "vendor_a_proposal.pdf",
    "content_type": "application/pdf",
    "size_bytes": 48213,
    "status": "ingested",
    "page_count": 6,
    "chunk_count": 24,
    "error": None,
    "uploaded_by": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
    "job_id": "f6a7b8c9-0000-4000-8000-000000000006",
    "created_at": "2026-07-26T12:00:00Z",
    "updated_at": "2026-07-26T12:00:10Z",
}


class DocumentRead(BaseModel):
    model_config = ConfigDict(from_attributes=True, json_schema_extra={"examples": [_DOC_EXAMPLE]})

    id: uuid.UUID
    filename: str
    title: str | None
    content_type: str | None
    size_bytes: int | None
    status: DocumentStatus
    page_count: int | None
    chunk_count: int
    error: str | None
    uploaded_by: uuid.UUID | None
    job_id: uuid.UUID | None
    created_at: datetime
    updated_at: datetime


class DocumentUploadResponse(BaseModel):
    """Returned by POST /documents — the document plus its ingestion job."""

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [{"document": _DOC_EXAMPLE, "ingestion_job_id": "f6a7b8c9-0000-4000-8000-000000000006"}]
        }
    )

    document: DocumentRead
    ingestion_job_id: uuid.UUID


class DocumentChunkRead(BaseModel):
    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "examples": [
                {
                    "id": "a7b8c9d0-0000-4000-8000-000000000007",
                    "document_id": "d4e5f6a7-0000-4000-8000-000000000004",
                    "chunk_index": 0,
                    "text": "Vendor A offers a 99.9% uptime SLA, holds SOC 2 Type II, and is priced at $50,000/year.",
                    "char_count": 88,
                    "page_number": 1,
                    "created_at": "2026-07-26T12:00:10Z",
                }
            ]
        },
    )

    id: uuid.UUID
    document_id: uuid.UUID
    chunk_index: int
    text: str
    char_count: int
    page_number: int | None
    created_at: datetime
