"""Health check endpoints.

``/health``     — liveness: the process is up and serving.
``/health/db``  — readiness: the database is reachable (runs ``SELECT 1``).
"""

from __future__ import annotations

import logging

from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.session import get_db
from app.schemas.health import DBHealthResponse, HealthResponse

logger = logging.getLogger(__name__)

router = APIRouter(tags=["health"])


@router.get("/health", response_model=HealthResponse, summary="Liveness probe")
def health() -> HealthResponse:
    """Return basic service status and metadata."""
    return HealthResponse(
        status="ok",
        app=settings.app_name,
        version=settings.app_version,
        env=settings.env,
    )


@router.get("/health/db", response_model=DBHealthResponse, summary="Database readiness probe")
def health_db(db: Session = Depends(get_db)) -> DBHealthResponse:
    """Verify database connectivity by issuing a trivial query."""
    try:
        db.execute(text("SELECT 1"))
        return DBHealthResponse(status="ok", database="reachable")
    except SQLAlchemyError as exc:  # pragma: no cover - exercised only when DB is down
        logger.warning("Database health check failed: %s", exc)
        return DBHealthResponse(status="degraded", database="unreachable")
