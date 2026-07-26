"""Pydantic schemas for documents and their chunks."""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.models.enums import DocumentStatus


class DocumentRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

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

    document: DocumentRead
    ingestion_job_id: uuid.UUID


class DocumentChunkRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    document_id: uuid.UUID
    chunk_index: int
    text: str
    char_count: int
    page_number: int | None
    created_at: datetime
