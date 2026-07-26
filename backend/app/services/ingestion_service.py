"""Document ingestion: parse → chunk → embed → store.

Runs as a background job (``JobType.INGESTION``), so it inherits progress
tracking, cancellation, retries and SSE streaming from Milestone 5.
"""

from __future__ import annotations

import logging
import uuid
from dataclasses import dataclass

from sqlalchemy import delete
from sqlalchemy.orm import Session

from app.agent.llm.base import LLMError
from app.agent.llm.embeddings import get_embedding_client
from app.core.config import settings
from app.models.document import Document, DocumentChunk
from app.models.enums import DocumentStatus
from app.services import job_service
from app.services.chunking import chunk_pages
from app.services.document_parser import UnsupportedDocument, extract_pages

logger = logging.getLogger(__name__)

_EMBED_BATCH = 32


@dataclass
class IngestionOutcome:
    success: bool = False
    cancelled: bool = False
    error: str | None = None
    chunks: int = 0


def run_ingestion(db: Session, job) -> IngestionOutcome:
    """Ingest the document referenced by ``job.input['document_id']``."""
    job_id = job.id
    params = dict(job.input or {})
    doc_id = params.get("document_id")
    if not doc_id:
        return IngestionOutcome(error="job.input.document_id is required")

    doc = db.get(Document, uuid.UUID(str(doc_id)))
    if doc is None:
        return IngestionOutcome(error=f"Document {doc_id} not found")

    doc.status = DocumentStatus.PROCESSING
    doc.job_id = job_id
    doc.error = None
    db.commit()

    # --- parse ---
    if not job_service.set_progress(db, job_id, 10, "parsing document"):
        return IngestionOutcome(cancelled=True)
    try:
        pages = extract_pages(doc.storage_path, doc.content_type)
    except (UnsupportedDocument, FileNotFoundError, OSError) as exc:
        return _fail(db, doc, f"parse failed: {exc}")

    text_len = sum(len(t or "") for _, t in pages)
    if text_len == 0:
        return _fail(db, doc, "no extractable text (is this a scanned PDF?)")

    # --- chunk ---
    if not job_service.set_progress(db, job_id, 30, "chunking text"):
        return IngestionOutcome(cancelled=True)
    chunks = chunk_pages(pages, size=settings.chunk_size, overlap=settings.chunk_overlap)
    if not chunks:
        return _fail(db, doc, "no chunks produced")

    # --- embed ---
    client = get_embedding_client()
    if client is None:
        return _fail(db, doc, "no embedding provider configured")

    # Replace any chunks from a previous attempt (idempotent re-runs).
    db.execute(delete(DocumentChunk).where(DocumentChunk.document_id == doc.id))
    db.commit()

    total = len(chunks)
    stored = 0
    for start in range(0, total, _EMBED_BATCH):
        if not job_service.is_running(db, job_id):
            return IngestionOutcome(cancelled=True)
        batch = chunks[start : start + _EMBED_BATCH]
        try:
            vectors = client.embed([c.text for c in batch])
        except LLMError as exc:
            return _fail(db, doc, f"embedding failed: {exc}")
        for chunk, vector in zip(batch, vectors, strict=False):
            db.add(
                DocumentChunk(
                    document_id=doc.id,
                    chunk_index=chunk.index,
                    text=chunk.text,
                    char_count=len(chunk.text),
                    page_number=chunk.page_number,
                    embedding=vector,
                )
            )
        db.commit()
        stored += len(batch)
        pct = 30 + int(stored / total * 60)  # 30% → 90%
        if not job_service.set_progress(db, job_id, pct, f"embedding chunks ({stored}/{total})"):
            return IngestionOutcome(cancelled=True)

    # --- finalize ---
    doc.status = DocumentStatus.INGESTED
    doc.chunk_count = stored
    doc.page_count = len([p for p, _ in pages if p is not None]) or None
    db.commit()
    job_service.set_progress(db, job_id, 95, "finalizing")
    logger.info("Ingested document %s: %s chunks", doc.id, stored)
    return IngestionOutcome(success=True, chunks=stored)


def _fail(db: Session, doc: Document, message: str) -> IngestionOutcome:
    logger.warning("Ingestion failed for document %s: %s", doc.id, message)
    doc.status = DocumentStatus.FAILED
    doc.error = message
    db.commit()
    return IngestionOutcome(error=message)
