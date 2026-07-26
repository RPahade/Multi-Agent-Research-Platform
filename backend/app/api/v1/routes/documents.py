"""Document endpoints — upload (triggers async ingestion), list, inspect, delete.

Reads: any authenticated user. Upload/delete: analyst + admin.
"""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, File, Query, Response, UploadFile, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, require_job_writer
from app.api.utils import get_active_or_404
from app.db.session import get_db
from app.models.document import Document
from app.models.enums import DocumentStatus, JobType
from app.models.user import User
from app.schemas.common import Page, PageParams
from app.schemas.document import DocumentChunkRead, DocumentRead, DocumentUploadResponse
from app.services import document_service, job_runner, job_service

router = APIRouter(prefix="/documents", tags=["documents"])

# Guard against accidentally huge uploads (25 MB).
_MAX_UPLOAD_BYTES = 25 * 1024 * 1024


@router.post(
    "",
    response_model=DocumentUploadResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Upload a document and start ingestion (async)",
)
async def upload_document(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    user: User = Depends(require_job_writer),
) -> DocumentUploadResponse:
    data = await file.read()
    if not data:
        raise _bad_request("Uploaded file is empty")
    if len(data) > _MAX_UPLOAD_BYTES:
        raise _bad_request(f"File too large (max {_MAX_UPLOAD_BYTES // (1024 * 1024)} MB)")

    path, size = document_service.save_upload(file.filename or "upload.bin", data)
    doc = document_service.create_document(
        db,
        filename=file.filename or "upload.bin",
        content_type=file.content_type,
        storage_path=path,
        size_bytes=size,
        uploaded_by=user.id,
    )
    # Ingestion (parse + chunk + embed) runs as a background job.
    job = job_service.create_job(
        db,
        job_type=JobType.INGESTION,
        input={"document_id": str(doc.id)},
        user_id=user.id,
    )
    doc.job_id = job.id
    db.commit()
    db.refresh(doc)
    job_runner.submit(job.id)
    return DocumentUploadResponse(document=DocumentRead.model_validate(doc), ingestion_job_id=job.id)


@router.get("", response_model=Page[DocumentRead], summary="List documents")
def list_documents(
    pg: PageParams = Depends(),
    status_filter: DocumentStatus | None = Query(default=None, alias="status"),
    q: str | None = Query(default=None, description="search filename"),
    db: Session = Depends(get_db),
    _user: User = Depends(get_current_user),
) -> Page[DocumentRead]:
    items, total = document_service.list_page(db, page=pg.page, size=pg.size, status=status_filter, q=q)
    return Page[DocumentRead].create([DocumentRead.model_validate(d) for d in items], total, pg)


@router.get("/{document_id}", response_model=DocumentRead, summary="Get a document")
def get_document(
    document_id: uuid.UUID,
    db: Session = Depends(get_db),
    _user: User = Depends(get_current_user),
) -> Document:
    return get_active_or_404(db, Document, document_id, "Document")


@router.get(
    "/{document_id}/chunks",
    response_model=Page[DocumentChunkRead],
    summary="Inspect a document's chunks (what RAG searches)",
)
def list_chunks(
    document_id: uuid.UUID,
    pg: PageParams = Depends(),
    db: Session = Depends(get_db),
    _user: User = Depends(get_current_user),
) -> Page[DocumentChunkRead]:
    doc = get_active_or_404(db, Document, document_id, "Document")
    items, total = document_service.list_chunks(db, doc.id, page=pg.page, size=pg.size)
    return Page[DocumentChunkRead].create(
        [DocumentChunkRead.model_validate(c) for c in items], total, pg
    )


@router.delete(
    "/{document_id}", status_code=status.HTTP_204_NO_CONTENT, summary="Delete a document (soft)"
)
def delete_document(
    document_id: uuid.UUID,
    db: Session = Depends(get_db),
    _user: User = Depends(require_job_writer),
) -> Response:
    doc = get_active_or_404(db, Document, document_id, "Document")
    document_service.soft_delete(db, doc)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


def _bad_request(detail: str):
    from fastapi import HTTPException

    return HTTPException(status.HTTP_400_BAD_REQUEST, detail)
