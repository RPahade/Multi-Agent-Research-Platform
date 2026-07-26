"""FastAPI application entrypoint.

Exposes ``create_app()`` (app factory) and a module-level ``app`` instance that
uvicorn runs (``uvicorn app.main:app``). OpenAPI docs are served automatically at
``/docs`` (Swagger) and ``/redoc``.
"""

from __future__ import annotations

import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1.router import api_router
from app.core.config import settings
from app.core.logging import configure_logging

logger = logging.getLogger(__name__)

_API_DESCRIPTION = """
Backend API for the **Multi-Agent Research Intelligence Platform**.

A single research **agent** orchestrates tools to ingest documents, retrieve relevant
passages (RAG), synthesise **cited** reports, and redact PII — all as resilient,
streamable background **jobs**, with **event-driven** updates over Kafka.

### Authentication
1. `POST /api/v1/auth/login` with your email + password (OAuth2 password form) to get an
   access token. In Swagger, click **Authorize** and log in — all protected calls then
   carry the token automatically.
2. Roles: **admin** (manage users/config), **analyst** (run research), **leadership** (read-only).

### Typical flow
`POST /documents` (upload) → poll the ingestion job → `POST /jobs` (research over the docs)
→ watch `GET /jobs/{id}/stream` (SSE) → read `GET /reports?job_id=...`.

Interactive docs: **/docs** (Swagger UI) · **/redoc** (ReDoc). Schema: **/openapi.json**.
""".strip()

_TAGS_METADATA = [
    {"name": "health", "description": "Liveness/readiness probes."},
    {"name": "auth", "description": "Login, token refresh (rotation), logout, and current user."},
    {"name": "users", "description": "User management (admin only)."},
    {"name": "agents", "description": "Configurable orchestrating agents. Writes: admin."},
    {"name": "tools", "description": "Configurable tools the agent can use. Writes: admin."},
    {"name": "reports", "description": "Generated cited reports and their version history."},
    {"name": "jobs", "description": "Async jobs: create, track progress, cancel, stream (SSE), per-tool steps."},
    {"name": "documents", "description": "Upload/ingest source documents (RAG) and inspect their chunks."},
    {"name": "mcp", "description": "Status of the external MCP tool server."},
    {"name": "events", "description": "Kafka event pipeline configuration."},
]


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
    """Application startup/shutdown hooks."""
    logger.info(
        "%s v%s started (env=%s)", settings.app_name, settings.app_version, settings.env
    )
    _seed_first_admin()

    from app.services import job_runner

    job_runner.recover_orphans()  # requeue jobs left running/pending by a prior process
    job_runner.start_reaper()  # detect & recover stale running jobs

    yield

    job_runner.stop_reaper()
    job_runner.shutdown()

    from app.services import event_publisher

    event_publisher.flush()
    logger.info("%s shutting down", settings.app_name)


def _seed_first_admin() -> None:
    """Create the bootstrap admin on startup if configured (best-effort)."""
    from app.db.session import SessionLocal
    from app.services.user_service import seed_first_admin

    try:
        with SessionLocal() as db:
            seed_first_admin(db)
    except Exception:  # noqa: BLE001 - never block startup on seeding
        logger.exception("First-admin seeding failed (continuing startup)")


def create_app() -> FastAPI:
    """Build and configure the FastAPI application."""
    configure_logging()

    app = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        description=_API_DESCRIPTION,
        summary="Agent-driven research: ingest documents, retrieve, synthesise cited reports.",
        contact={"name": "Multi-Agent Research Platform"},
        license_info={"name": "Proprietary"},
        openapi_tags=_TAGS_METADATA,
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
        lifespan=lifespan,
    )

    # CORS — allow the Angular frontend (and other configured origins) to call the API.
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Mount versioned API routes under the configured prefix.
    app.include_router(api_router, prefix=settings.api_v1_prefix)

    @app.get("/", tags=["root"], summary="Service root")
    def root() -> dict[str, str]:
        """Friendly root pointer to the docs."""
        return {
            "service": settings.app_name,
            "version": settings.app_version,
            "docs": "/docs",
            "health": f"{settings.api_v1_prefix}/health",
        }

    return app


app = create_app()
