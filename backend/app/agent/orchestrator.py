"""Sequential single-agent orchestrator (Milestone 6, step 1).

Runs the tool pipeline in order inside a job:
- records each tool as a `job_steps` row (status/output/error/timings),
- updates job progress + current_step between tools (so SSE/polling see it live),
- checks for cancellation cooperatively,
- applies the partial-failure policy (required tool fails -> stop; optional -> continue),
- writes the final report (create, or update+version on a retry).

No LLM yet — tools are deterministic stubs. The runner (M5) handles retries/recovery.
"""

from __future__ import annotations

import logging
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone

from sqlalchemy import delete
from sqlalchemy.orm import Session

from app.agent.base import ToolContext
from app.agent.tools import build_pipeline
from app.models.enums import JobStepStatus, ReportStatus
from app.models.job import Job
from app.models.job_step import JobStep
from app.services import job_service, report_service

logger = logging.getLogger(__name__)


@dataclass
class OrchestrationOutcome:
    success: bool = False
    cancelled: bool = False
    error: str | None = None
    warnings: list[str] = field(default_factory=list)


def _now() -> datetime:
    return datetime.now(timezone.utc)


def run(db: Session, job: Job) -> OrchestrationOutcome:
    """Execute the pipeline for a running research job."""
    # Capture primitives up front (ORM object expires across commits).
    job_id: uuid.UUID = job.id
    user_id = job.user_id
    params = dict(job.input or {})
    tool_seconds = float(params.get("tool_seconds", 0.4))

    ctx = ToolContext(job_id=job_id, user_id=user_id, input=params)
    pipeline = build_pipeline()
    total = len(pipeline)
    warnings: list[str] = []

    # Fresh run: clear any steps from a previous attempt.
    db.execute(delete(JobStep).where(JobStep.job_id == job_id))
    db.commit() 

    for i, tool in enumerate(pipeline, start=1):
        if not job_service.is_running(db, job_id):
            return OrchestrationOutcome(cancelled=True)

        step = JobStep(
            job_id=job_id, sequence=i, tool_key=tool.key, name=tool.name,
            required=tool.required, status=JobStepStatus.RUNNING, started_at=_now(),
        )
        db.add(step)
        db.commit()

        time.sleep(tool_seconds)  # makes progress observable (removed once tools do real work)

        try:
            result = tool.run(ctx)
        except Exception as exc:  # noqa: BLE001 - a crashing tool is a failed step, not a crash
            logger.exception("Tool %s raised", tool.key)
            result = _failed_result(exc)

        succeeded = result.status == "succeeded"
        step.status = JobStepStatus.SUCCEEDED if succeeded else JobStepStatus.FAILED
        step.output = result.output
        step.error = result.error
        step.finished_at = _now()
        db.commit()

        # Update job progress; conditional update returns False if cancelled mid-step.
        if not job_service.set_progress(db, job_id, int(i / total * 100), tool.name):
            return OrchestrationOutcome(cancelled=True)

        if not succeeded:
            if tool.required:
                logger.info("Job %s: required tool '%s' failed -> stopping", job_id, tool.key)
                return OrchestrationOutcome(success=False, error=f"Required tool '{tool.key}' failed: {result.error}")
            logger.info("Job %s: optional tool '%s' failed -> continuing", job_id, tool.key)
            warnings.append(f"{tool.key}: {result.error}")

    _write_report(db, job_id, user_id, ctx, warnings)
    return OrchestrationOutcome(success=True, warnings=warnings)


def _failed_result(exc: Exception):
    from app.agent.base import ToolResult

    return ToolResult.failed(f"{type(exc).__name__}: {exc}")


def _write_report(db: Session, job_id, user_id, ctx: ToolContext, warnings: list[str]) -> None:
    """Persist the pipeline's report artifact (create, or update+version on retry)."""
    content = dict(ctx.artifacts.get("report") or {"title": "Research Report", "sections": []})
    if warnings:
        content["warnings"] = warnings
    title = content.get("title", "Research Report")
    summary = content.get("summary")

    existing = report_service.get_by_job_id(db, job_id)
    if existing is not None:
        report_service.update(
            db, existing,
            {"title": title, "summary": summary, "content": content, "status": ReportStatus.FINAL},
            actor_id=user_id,
        )
    else:
        report_service.create(
            db,
            {"job_id": job_id, "title": title, "summary": summary,
             "content": content, "status": ReportStatus.FINAL},
            created_by=user_id,
        )
