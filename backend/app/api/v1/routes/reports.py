"""Report CRUD endpoints.

Reads: any authenticated user. Writes: analyst + admin (leadership is read-only).
Updates snapshot the previous state into report_versions and bump the version.
"""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, require_report_writer
from app.api.utils import get_active_or_404
from app.db.session import get_db
from app.models.report import Report
from app.models.user import User
from app.schemas.chat import ChatRequest, ChatResponse
from app.schemas.common import Page, PageParams
from app.schemas.report import ReportCreate, ReportRead, ReportUpdate, ReportVersionRead
from app.models.enums import ReportStatus
from app.services import chat_service, report_service
from app.services.chat_service import ChatUnavailable

router = APIRouter(prefix="/reports", tags=["reports"])


@router.get("", response_model=Page[ReportRead], summary="List reports")
def list_reports(
    pg: PageParams = Depends(),
    status_filter: ReportStatus | None = Query(default=None, alias="status"),
    job_id: uuid.UUID | None = Query(default=None),
    q: str | None = Query(default=None, description="search title"),
    db: Session = Depends(get_db),
    _user: User = Depends(get_current_user),
) -> Page[ReportRead]:
    items, total = report_service.list_page(
        db, page=pg.page, size=pg.size, status=status_filter, job_id=job_id, q=q
    )
    return Page[ReportRead].create([ReportRead.model_validate(r) for r in items], total, pg)


@router.get("/{report_id}", response_model=ReportRead, summary="Get a report")
def get_report(
    report_id: uuid.UUID,
    db: Session = Depends(get_db),
    _user: User = Depends(get_current_user),
) -> Report:
    return get_active_or_404(db, Report, report_id, "Report")


@router.get(
    "/{report_id}/versions",
    response_model=list[ReportVersionRead],
    summary="List a report's version history",
)
def list_report_versions(
    report_id: uuid.UUID,
    db: Session = Depends(get_db),
    _user: User = Depends(get_current_user),
) -> list:
    report = get_active_or_404(db, Report, report_id, "Report")
    return report_service.list_versions(db, report)


@router.post(
    "/{report_id}/chat",
    response_model=ChatResponse,
    summary="Ask a grounded question about a report",
)
def chat_with_report(
    report_id: uuid.UUID,
    payload: ChatRequest,
    db: Session = Depends(get_db),
    _user: User = Depends(get_current_user),
) -> dict:
    """Answer a question using only the report's content + a fresh retrieval over its
    source documents. Returns citations and a ``grounded`` flag; 503 if the LLM is down."""
    report = get_active_or_404(db, Report, report_id, "Report")
    try:
        return chat_service.answer_report_question(db, report, payload.message, payload.history)
    except ChatUnavailable as exc:
        raise HTTPException(
            status.HTTP_503_SERVICE_UNAVAILABLE,
            f"Chat is temporarily unavailable: {exc}",
        ) from exc


@router.post("", response_model=ReportRead, status_code=status.HTTP_201_CREATED, summary="Create a report")
def create_report(
    payload: ReportCreate,
    db: Session = Depends(get_db),
    user: User = Depends(require_report_writer),
) -> Report:
    if payload.job_id is not None and report_service.get_by_job_id(db, payload.job_id) is not None:
        raise HTTPException(status.HTTP_409_CONFLICT, "A report already exists for this job")
    return report_service.create(db, payload.model_dump(), created_by=user.id)


@router.patch("/{report_id}", response_model=ReportRead, summary="Update a report (snapshots a new version)")
def update_report(
    report_id: uuid.UUID,
    payload: ReportUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(require_report_writer),
) -> Report:
    report = get_active_or_404(db, Report, report_id, "Report")
    return report_service.update(db, report, payload.model_dump(exclude_unset=True), actor_id=user.id)


@router.delete("/{report_id}", status_code=status.HTTP_204_NO_CONTENT, summary="Delete a report (soft)")
def delete_report(
    report_id: uuid.UUID,
    db: Session = Depends(get_db),
    _user: User = Depends(require_report_writer),
) -> Response:
    report = get_active_or_404(db, Report, report_id, "Report")
    report_service.soft_delete(db, report)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
