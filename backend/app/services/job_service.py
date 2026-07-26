"""Job CRUD-style business logic (API-facing)."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app.models.enums import JobStatus, JobType
from app.models.job import Job
from app.models.job_step import JobStep
from app.services import crud, event_publisher

# Statuses from which a job can still be cancelled.
_CANCELLABLE = (JobStatus.PENDING, JobStatus.RUNNING)


def is_running(db: Session, job_id: uuid.UUID) -> bool:
    """Whether the job is currently in the running state (used for cancel checks)."""
    return db.execute(select(Job.status).where(Job.id == job_id)).scalar() == JobStatus.RUNNING


def set_progress(db: Session, job_id: uuid.UUID, progress: int, current_step: str) -> bool:
    """Conditionally update progress/current_step/heartbeat only while running.

    Returns False if the row was not updated (e.g. the job was cancelled).
    """
    result = db.execute(
        update(Job)
        .where(Job.id == job_id, Job.status == JobStatus.RUNNING)
        .values(progress=progress, current_step=current_step, last_heartbeat=datetime.now(timezone.utc))
    )
    db.commit()
    updated = result.rowcount > 0
    if updated:
        event_publisher.publish_status(
            job_id, JobStatus.RUNNING, event_type="job.progress",
            progress=progress, current_step=current_step,
        )
    return updated


def list_steps(db: Session, job_id: uuid.UUID) -> list[JobStep]:
    return list(
        db.scalars(select(JobStep).where(JobStep.job_id == job_id).order_by(JobStep.sequence))
    )


def create_job(
    db: Session,
    *,
    job_type: JobType,
    input: dict,
    user_id: uuid.UUID,
    agent_id: uuid.UUID | None = None,
    idempotency_key: str | None = None,
    max_attempts: int = 3,
) -> Job:
    job = Job(
        type=job_type,
        input=input or {},
        user_id=user_id,
        agent_id=agent_id,
        status=JobStatus.PENDING,
        idempotency_key=idempotency_key,
        max_attempts=max_attempts,
    )
    db.add(job)
    db.commit()
    db.refresh(job)
    event_publisher.publish_status(job.id, JobStatus.PENDING, event_type="job.created")
    return job


def get_job(db: Session, job_id: uuid.UUID) -> Job | None:
    return db.get(Job, job_id)


def get_by_idempotency_key(db: Session, user_id: uuid.UUID, key: str) -> Job | None:
    return db.scalar(
        select(Job).where(Job.user_id == user_id, Job.idempotency_key == key)
    )


def list_page(
    db: Session,
    *,
    page: int,
    size: int,
    status: JobStatus | None = None,
    job_type: JobType | None = None,
    user_id: uuid.UUID | None = None,
) -> tuple[list[Job], int]:
    stmt = select(Job)
    if status is not None:
        stmt = stmt.where(Job.status == status)
    if job_type is not None:
        stmt = stmt.where(Job.type == job_type)
    if user_id is not None:
        stmt = stmt.where(Job.user_id == user_id)
    stmt = stmt.order_by(Job.created_at.desc())
    return crud.paginate(db, stmt, page, size)


def request_cancel(db: Session, job_id: uuid.UUID) -> bool:
    """Cancel a pending/running job. Returns True if it was cancellable."""
    result = db.execute(
        update(Job)
        .where(Job.id == job_id, Job.status.in_(_CANCELLABLE))
        .values(status=JobStatus.CANCELLED, finished_at=datetime.now(timezone.utc))
    )
    db.commit()
    cancelled = result.rowcount > 0
    if cancelled:
        event_publisher.publish_status(job_id, JobStatus.CANCELLED, event_type="job.cancelled")
    return cancelled
