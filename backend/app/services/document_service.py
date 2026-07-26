"""Document CRUD + file storage + vector retrieval."""

from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.document import Document, DocumentChunk
from app.models.enums import DocumentStatus
from app.services import crud

logger = logging.getLogger(__name__)


def save_upload(filename: str, data: bytes) -> tuple[str, int]:
    """Write the uploaded bytes to the uploads volume; return (path, size)."""
    base = Path(settings.upload_dir)
    base.mkdir(parents=True, exist_ok=True)
    safe = Path(filename).name  # strip any directory components
    target = base / f"{uuid.uuid4().hex}_{safe}"
    target.write_bytes(data)
    return str(target), len(data)


def create_document(
    db: Session,
    *,
    filename: str,
    content_type: str | None,
    storage_path: str,
    size_bytes: int,
    uploaded_by: uuid.UUID | None,
    title: str | None = None,
) -> Document:
    doc = Document(
        filename=filename,
        title=title or filename,
        content_type=content_type,
        storage_path=storage_path,
        size_bytes=size_bytes,
        uploaded_by=uploaded_by,
        status=DocumentStatus.UPLOADED,
    )
    db.add(doc)
    db.commit()
    db.refresh(doc)
    return doc


def get_document(db: Session, doc_id: uuid.UUID) -> Document | None:
    doc = db.get(Document, doc_id)
    if doc is None or doc.deleted_at is not None:
        return None
    return doc


def list_page(
    db: Session, *, page: int, size: int, status: DocumentStatus | None = None, q: str | None = None
) -> tuple[list[Document], int]:
    stmt = select(Document).where(Document.deleted_at.is_(None))
    if status is not None:
        stmt = stmt.where(Document.status == status)
    if q:
        stmt = stmt.where(Document.filename.ilike(f"%{q}%"))
    stmt = stmt.order_by(Document.created_at.desc())
    return crud.paginate(db, stmt, page, size)


def list_chunks(db: Session, doc_id: uuid.UUID, *, page: int, size: int) -> tuple[list[DocumentChunk], int]:
    stmt = (
        select(DocumentChunk)
        .where(DocumentChunk.document_id == doc_id)
        .order_by(DocumentChunk.chunk_index)
    )
    return crud.paginate(db, stmt, page, size)


def soft_delete(db: Session, doc: Document) -> None:
    doc.deleted_at = datetime.now(timezone.utc)
    db.commit()


def search_chunks(
    db: Session,
    query_embedding: list[float],
    *,
    top_k: int,
    document_ids: list[uuid.UUID] | None = None,
) -> list[tuple[DocumentChunk, Document, float]]:
    """Vector similarity search: nearest chunks by cosine distance.

    Returns ``[(chunk, document, distance), ...]`` ordered most-similar first.
    """
    distance = DocumentChunk.embedding.cosine_distance(query_embedding).label("distance")
    stmt = (
        select(DocumentChunk, Document, distance)
        .join(Document, Document.id == DocumentChunk.document_id)
        .where(
            DocumentChunk.embedding.is_not(None),
            Document.deleted_at.is_(None),
            Document.status == DocumentStatus.INGESTED,
        )
    )
    if document_ids:
        stmt = stmt.where(DocumentChunk.document_id.in_(document_ids))
    stmt = stmt.order_by(distance).limit(top_k)
    return [(row[0], row[1], float(row[2])) for row in db.execute(stmt).all()]
