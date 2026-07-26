"""In-process background job runner with retries, recovery, and a reaper.

Execution is driven through the DB with *conditional* updates (``WHERE status='running'``)
so a cancelled or externally-changed job is never resurrected.

Resilience (Milestone 5, step 2):
- **Retries**: a failed run is requeued until ``attempts`` reaches ``max_attempts``.
- **Startup recovery**: orphaned ``running`` jobs (crashed process) and un-picked ``pending``
  jobs are recovered/resubmitted when the app starts.
- **Reaper**: a background thread requeues ``running`` jobs whose ``last_heartbeat`` went stale
  (a worker that died/hung in a still-alive process).
"""

from __future__ import annotations

import logging
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone

from sqlalchemy import select, update

from app.core.config import settings
from app.db.session import SessionLocal
from app.models.enums import JobStatus, JobType
from app.models.job import Job

logger = logging.getLogger(__name__)

_executor = ThreadPoolExecutor(max_workers=4, thread_name_prefix="jobworker")

_DEFAULT_STEPS = [
    "ingesting documents",
    "researching web",
    "verifying citations",
    "formatting report",
]


def _now() -> datetime:
    return datetime.now(timezone.utc)


# --- Public API --------------------------------------------------------------

def submit(job_id) -> None:
    """Schedule a job to run in the background."""
    _executor.submit(_run, job_id)


def shutdown() -> None:
    """Stop the worker pool (called on app shutdown)."""
    _executor.shutdown(wait=False, cancel_futures=True)


def recover_orphans() -> None:
    """Recover jobs left behind by a crashed/restarted process.

    Called once on startup: orphaned ``running`` jobs are requeued (or failed if out
    of attempts), and any ``pending`` jobs are resubmitted.
    """
    try:
        with SessionLocal() as db:
            # Snapshot pending ids BEFORE recovering running jobs (which create new pendings).
            pending_ids = list(db.scalars(select(Job.id).where(Job.status == JobStatus.PENDING)))
            running = list(db.scalars(select(Job).where(Job.status == JobStatus.RUNNING)))
            for job in running:
                logger.warning("Recovering orphaned running job %s", job.id)
                _recover_running(db, job)
            for jid in pending_ids:
                logger.info("Resubmitting pending job %s", jid)
                submit(jid)
    except Exception:  # noqa: BLE001 - never block startup
        logger.exception("Orphan recovery failed")


# --- Reaper ------------------------------------------------------------------

_reaper_stop = threading.Event()
_reaper_thread: threading.Thread | None = None


def start_reaper() -> None:
    global _reaper_thread
    _reaper_stop.clear()
    _reaper_thread = threading.Thread(target=_reaper_loop, name="job-reaper", daemon=True)
    _reaper_thread.start()
    logger.info("Job reaper started (interval=%ss, stale=%ss)",
                settings.job_reaper_interval_seconds, settings.job_heartbeat_stale_seconds)


def stop_reaper() -> None:
    _reaper_stop.set()


def _reaper_loop() -> None:
    interval = settings.job_reaper_interval_seconds
    stale_seconds = settings.job_heartbeat_stale_seconds
    while not _reaper_stop.wait(interval):
        try:
            with SessionLocal() as db:
                threshold = _now() - timedelta(seconds=stale_seconds)
                stale = list(
                    db.scalars(
                        select(Job).where(
                            Job.status == JobStatus.RUNNING,
                            Job.last_heartbeat.is_not(None),
                            Job.last_heartbeat < threshold,
                        )
                    )
                )
                for job in stale:
                    logger.warning("Reaper recovering stale job %s (heartbeat %s)", job.id, job.last_heartbeat)
                    _recover_running(db, job)
        except Exception:  # noqa: BLE001
            logger.exception("Reaper loop error")


# --- Internal execution ------------------------------------------------------

def _recover_running(db, job: Job) -> None:
    """Requeue an interrupted ``running`` job, or fail it if out of attempts."""
    if job.attempts < job.max_attempts:
        result = db.execute(
            update(Job)
            .where(Job.id == job.id, Job.status == JobStatus.RUNNING)
            .values(status=JobStatus.PENDING, progress=0, current_step=None,
                    last_heartbeat=None, error="Recovered after interruption")
        )
        db.commit()
        if result.rowcount > 0:
            submit(job.id)
    else:
        db.execute(
            update(Job)
            .where(Job.id == job.id, Job.status == JobStatus.RUNNING)
            .values(status=JobStatus.FAILED, error="Interrupted; no retries left", finished_at=_now())
        )
        db.commit()


def _fail_or_retry(db, job_id, attempt_no: int, max_attempts: int, error: str) -> None:
    if attempt_no < max_attempts:
        result = db.execute(
            update(Job)
            .where(Job.id == job_id, Job.status == JobStatus.RUNNING)
            .values(status=JobStatus.PENDING, progress=0, current_step=None, last_heartbeat=None, error=error)
        )
        db.commit()
        if result.rowcount > 0:
            logger.info("Job %s failed attempt %s/%s; retrying", job_id, attempt_no, max_attempts)
            submit(job_id)
    else:
        db.execute(
            update(Job)
            .where(Job.id == job_id, Job.status == JobStatus.RUNNING)
            .values(status=JobStatus.FAILED, error=error, finished_at=_now())
        )
        db.commit()
        logger.info("Job %s failed permanently after %s attempts", job_id, attempt_no)


def _run(job_id) -> None:
    try:
        with SessionLocal() as db:
            _execute(db, job_id)
    except Exception:  # noqa: BLE001 - isolate worker crashes and retry
        logger.exception("Job %s crashed unexpectedly", job_id)
        try:
            with SessionLocal() as db:
                attempt_no = db.execute(select(Job.attempts).where(Job.id == job_id)).scalar() or 0
                max_attempts = db.execute(select(Job.max_attempts).where(Job.id == job_id)).scalar() or 1
                _fail_or_retry(db, job_id, attempt_no, max_attempts, "Internal worker error")
        except Exception:  # noqa: BLE001
            logger.exception("Failed to handle crash for job %s", job_id)


def _execute(db, job_id) -> None:
    job = db.get(Job, job_id)
    if job is None:
        logger.warning("Job %s not found; skipping", job_id)
        return

    params = job.input or {}
    n_steps = int(params.get("steps") or 0)
    labels = [f"step {i + 1}" for i in range(n_steps)] if n_steps > 0 else list(_DEFAULT_STEPS)
    total = len(labels)
    step_seconds = float(params.get("step_seconds", 1))
    fail = bool(params.get("fail"))
    fail_times = int(params.get("fail_times", 1))
    fail_step = int(params.get("fail_step", 1))

    # pending -> running (atomic; increments attempts; no-op if cancelled/not pending)
    started = db.execute(
        update(Job)
        .where(Job.id == job_id, Job.status == JobStatus.PENDING)
        .values(status=JobStatus.RUNNING, started_at=_now(), last_heartbeat=_now(),
                progress=0, current_step=None, error=None, attempts=Job.attempts + 1)
    )
    db.commit()
    if started.rowcount == 0:
        logger.info("Job %s not started (already cancelled or not pending)", job_id)
        return

    attempt_no = db.execute(select(Job.attempts).where(Job.id == job_id)).scalar()
    max_attempts = db.execute(select(Job.max_attempts).where(Job.id == job_id)).scalar()
    should_fail = fail and attempt_no <= fail_times
    logger.info("Job %s attempt %s/%s started", job_id, attempt_no, max_attempts)

    # Milestone 6: research jobs run the real agent orchestration pipeline.
    if job.type == JobType.RESEARCH:
        from app.agent import orchestrator

        outcome = orchestrator.run(db, job)
        if outcome.cancelled:
            logger.info("Job %s cancelled during orchestration", job_id)
            return
        if outcome.success:
            db.execute(
                update(Job)
                .where(Job.id == job_id, Job.status == JobStatus.RUNNING)
                .values(status=JobStatus.SUCCEEDED, progress=100, current_step="completed",
                        finished_at=_now(), last_heartbeat=_now())
            )
            db.commit()
            logger.info("Job %s orchestration succeeded", job_id)
        else:
            _fail_or_retry(db, job_id, attempt_no, max_attempts, outcome.error or "Orchestration failed")
        return

    # Milestone 6 step 3: ingestion jobs parse + chunk + embed an uploaded document.
    if job.type == JobType.INGESTION:
        from app.services import ingestion_service

        outcome = ingestion_service.run_ingestion(db, job)
        if outcome.cancelled:
            logger.info("Job %s cancelled during ingestion", job_id)
            return
        if outcome.success:
            db.execute(
                update(Job)
                .where(Job.id == job_id, Job.status == JobStatus.RUNNING)
                .values(status=JobStatus.SUCCEEDED, progress=100,
                        current_step=f"ingested {outcome.chunks} chunks",
                        finished_at=_now(), last_heartbeat=_now())
            )
            db.commit()
            logger.info("Job %s ingestion succeeded (%s chunks)", job_id, outcome.chunks)
        else:
            _fail_or_retry(db, job_id, attempt_no, max_attempts, outcome.error or "Ingestion failed")
        return

    # Other job types: the simulated pipeline (used for testing progress/cancel/retries).
    for i, label in enumerate(labels, start=1):
        status = db.execute(select(Job.status).where(Job.id == job_id)).scalar()
        if status != JobStatus.RUNNING:
            logger.info("Job %s stopping early (status=%s)", job_id, status)
            return

        time.sleep(step_seconds)  # simulate work

        if should_fail and i == fail_step:
            _fail_or_retry(db, job_id, attempt_no, max_attempts,
                           f"Simulated failure at '{label}' (attempt {attempt_no})")
            return

        progress = int(i / total * 100)
        updated = db.execute(
            update(Job)
            .where(Job.id == job_id, Job.status == JobStatus.RUNNING)
            .values(progress=progress, current_step=label, last_heartbeat=_now())
        )
        db.commit()
        if updated.rowcount == 0:
            logger.info("Job %s cancelled mid-run", job_id)
            return

    db.execute(
        update(Job)
        .where(Job.id == job_id, Job.status == JobStatus.RUNNING)
        .values(status=JobStatus.SUCCEEDED, progress=100, current_step="completed",
                finished_at=_now(), last_heartbeat=_now())
    )
    db.commit()
    logger.info("Job %s succeeded on attempt %s", job_id, attempt_no)
