"""Job endpoints — create (async), track progress, and cancel.

Reads: any authenticated user. Create/cancel: analyst + admin.
"""

from __future__ import annotations

import asyncio
import json
import uuid
from typing import Annotated

from fastapi import APIRouter, Body, Depends, Header, HTTPException, Query, Request, Response, status
from fastapi.responses import StreamingResponse
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_current_user_sse, require_job_writer
from app.db.session import SessionLocal, get_db
from app.models.enums import JobStatus, JobType
from app.models.job import Job
from app.models.user import User
from app.schemas.common import Page, PageParams
from app.schemas.job import JobCreate, JobRead
from app.schemas.job_step import JobStepRead
from app.services import job_runner, job_service

router = APIRouter(prefix="/jobs", tags=["jobs"])

_TERMINAL = {JobStatus.SUCCEEDED.value, JobStatus.FAILED.value, JobStatus.CANCELLED.value}

# Named request examples shown in Swagger's "Try it out" dropdown.
_JOB_EXAMPLES = {
    "rag_research": {
        "summary": "Research over uploaded documents (RAG)",
        "description": "Retrieves the top-K chunks from the given ingested documents and writes a cited report.",
        "value": {
            "type": "research",
            "input": {
                "query": "Compare Vendor A and Vendor B on data residency and pricing",
                "document_ids": ["d4e5f6a7-0000-4000-8000-000000000004"],
                "top_k": 8,
            },
        },
    },
    "inline_sources": {
        "summary": "Research with inline source text (no upload)",
        "description": "Provide source text directly; the agent cites it. Useful without documents.",
        "value": {
            "type": "research",
            "input": {
                "query": "Which vendor stores data in the EU?",
                "sources": [
                    {"title": "Vendor A Proposal", "text": "Vendor A hosts data exclusively in US regions."},
                    {"title": "Vendor B Contract", "text": "Vendor B stores customer data in the EU (Frankfurt, Dublin)."},
                ],
            },
        },
    },
    "simulated": {
        "summary": "Simulated job (test progress/cancel/retry)",
        "description": "Runs a timed placeholder pipeline. Use fail/fail_times to exercise the retry path.",
        "value": {"type": "research", "input": {"steps": 6, "step_seconds": 1}},
    },
}


def _get_or_404(db: Session, job_id: uuid.UUID) -> Job:
    job = job_service.get_job(db, job_id)
    if job is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Job not found")
    return job


@router.post(
    "",
    response_model=JobRead,
    status_code=status.HTTP_201_CREATED,
    summary="Create a job and start it in the background",
)
def create_job(
    payload: Annotated[JobCreate, Body(openapi_examples=_JOB_EXAMPLES)],
    response: Response,
    db: Session = Depends(get_db),
    user: User = Depends(require_job_writer),
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
) -> Job:
    # Idempotency: a repeated key returns the existing job instead of creating a duplicate.
    if idempotency_key:
        existing = job_service.get_by_idempotency_key(db, user.id, idempotency_key)
        if existing is not None:
            response.status_code = status.HTTP_200_OK
            return existing

    try:
        job = job_service.create_job(
            db,
            job_type=payload.type,
            input=payload.input,
            user_id=user.id,
            agent_id=payload.agent_id,
            idempotency_key=idempotency_key,
            max_attempts=payload.max_attempts,
        )
    except IntegrityError:
        # Concurrent request won the unique key; return the winner.
        db.rollback()
        existing = job_service.get_by_idempotency_key(db, user.id, idempotency_key)
        if existing is not None:
            response.status_code = status.HTTP_200_OK
            return existing
        raise

    job_runner.submit(job.id)  # returns immediately; runs asynchronously
    return job


@router.get("", response_model=Page[JobRead], summary="List jobs (paginated, filtered)")
def list_jobs(
    pg: PageParams = Depends(),
    status_filter: JobStatus | None = Query(default=None, alias="status"),
    type_filter: JobType | None = Query(default=None, alias="type"),
    db: Session = Depends(get_db),
    _user: User = Depends(get_current_user),
) -> Page[JobRead]:
    items, total = job_service.list_page(
        db, page=pg.page, size=pg.size, status=status_filter, job_type=type_filter
    )
    return Page[JobRead].create([JobRead.model_validate(j) for j in items], total, pg)


@router.get("/{job_id}", response_model=JobRead, summary="Get a job's status & progress")
def get_job(
    job_id: uuid.UUID,
    db: Session = Depends(get_db),
    _user: User = Depends(get_current_user),
) -> Job:
    return _get_or_404(db, job_id)


@router.get(
    "/{job_id}/steps",
    response_model=list[JobStepRead],
    summary="List a job's tool steps (orchestration trace)",
)
def list_job_steps(
    job_id: uuid.UUID,
    db: Session = Depends(get_db),
    _user: User = Depends(get_current_user),
) -> list:
    _get_or_404(db, job_id)
    return job_service.list_steps(db, job_id)


@router.post("/{job_id}/cancel", response_model=JobRead, summary="Cancel a pending/running job")
def cancel_job(
    job_id: uuid.UUID,
    db: Session = Depends(get_db),
    _user: User = Depends(require_job_writer),
) -> Job:
    job = _get_or_404(db, job_id)
    cancelled = job_service.request_cancel(db, job_id)
    if not cancelled:
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            f"Job cannot be cancelled (status={job.status.value})",
        )
    db.refresh(job)
    return job


# --- Live status streaming (SSE) ---------------------------------------------

def _fetch_status(job_id: uuid.UUID) -> dict | None:
    """Read a lightweight status snapshot in a short-lived session."""
    with SessionLocal() as db:
        job = db.get(Job, job_id)
        if job is None:
            return None
        return {
            "id": str(job.id),
            "status": job.status.value,
            "progress": job.progress,
            "current_step": job.current_step,
            "attempts": job.attempts,
            "error": job.error,
        }


def _sse(data: dict) -> str:
    return f"data: {json.dumps(data)}\n\n"


@router.get("/{job_id}/stream", summary="Stream live job status updates (SSE)")
async def stream_job(
    job_id: uuid.UUID,
    request: Request,
    _user: User = Depends(get_current_user_sse),
) -> StreamingResponse:
    """Server-Sent Events stream of a job's status/progress until it is terminal.

    Emits an event on every change; sends a ``: ping`` comment when idle to keep the
    connection alive; closes once the job succeeds/fails/is cancelled.
    """
    initial = await asyncio.to_thread(_fetch_status, job_id)
    if initial is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Job not found")

    async def event_generator():
        yield _sse(initial)
        last_key = (initial["status"], initial["progress"], initial["current_step"])
        if initial["status"] in _TERMINAL:
            return

        interval = 0.5
        elapsed = 0.0
        idle = 0.0
        max_seconds = 600.0
        while elapsed < max_seconds:
            if await request.is_disconnected():
                break
            await asyncio.sleep(interval)
            elapsed += interval
            snap = await asyncio.to_thread(_fetch_status, job_id)
            if snap is None:
                yield _sse({"error": "job no longer exists"})
                break
            key = (snap["status"], snap["progress"], snap["current_step"])
            if key != last_key:
                last_key = key
                idle = 0.0
                yield _sse(snap)
            else:
                idle += interval
                if idle >= 15.0:  # keep-alive ping for proxies
                    idle = 0.0
                    yield ": ping\n\n"
            if snap["status"] in _TERMINAL:
                break

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
