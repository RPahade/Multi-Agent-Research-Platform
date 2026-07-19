"""Report CRUD business logic, including version snapshots.

Each version's state (title/summary/content) is captured in report_versions:
- create   -> report.version = 1 and a v1 snapshot
- update   -> report.version += 1 and a matching snapshot
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.enums import ReportStatus
from app.models.report import Report, ReportVersion
from app.services import crud


def get_by_job_id(db: Session, job_id: uuid.UUID) -> Report | None:
    return db.scalar(select(Report).where(Report.job_id == job_id, Report.deleted_at.is_(None)))


def list_page(
    db: Session,
    *,
    page: int,
    size: int,
    status: ReportStatus | None = None,
    job_id: uuid.UUID | None = None,
    q: str | None = None,
) -> tuple[list[Report], int]:
    stmt = select(Report).where(Report.deleted_at.is_(None))
    if status is not None:
        stmt = stmt.where(Report.status == status)
    if job_id is not None:
        stmt = stmt.where(Report.job_id == job_id)
    if q:
        stmt = stmt.where(Report.title.ilike(f"%{q}%"))
    stmt = stmt.order_by(Report.created_at.desc())
    return crud.paginate(db, stmt, page, size)


def _snapshot(db: Session, report: Report, created_by: uuid.UUID | None) -> None:
    db.add(
        ReportVersion(
            report_id=report.id,
            version=report.version,
            title=report.title,
            summary=report.summary,
            content=report.content,
            created_by=created_by,
        )
    )


def create(db: Session, data: dict, *, created_by: uuid.UUID) -> Report:
    report = Report(**data, created_by=created_by, version=1)
    db.add(report)
    db.flush()  # assign id/defaults before snapshotting
    _snapshot(db, report, created_by)
    db.commit()
    db.refresh(report)
    return report


def update(db: Session, report: Report, data: dict, *, actor_id: uuid.UUID) -> Report:
    for field, value in data.items():
        setattr(report, field, value)
    report.version += 1
    db.flush()
    _snapshot(db, report, actor_id)
    db.commit()
    db.refresh(report)
    return report


def list_versions(db: Session, report: Report) -> list[ReportVersion]:
    return list(
        db.scalars(
            select(ReportVersion)
            .where(ReportVersion.report_id == report.id)
            .order_by(ReportVersion.version)
        )
    )


def soft_delete(db: Session, report: Report) -> None:
    report.deleted_at = datetime.now(timezone.utc)
    db.commit()
