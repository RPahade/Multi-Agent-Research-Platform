# CHANGELOG

All notable changes to this project, logged per session/milestone.
Format is loosely based on [Keep a Changelog](https://keepachangelog.com/).
For the *current overall state*, see [WORKING.md](WORKING.md).

---

## [Milestone 2 — Database Design] — 2026-07-19

**Goal:** Design and implement the database schema for core entities (Users, Agent,
Tools, Reports, Jobs), with migrations, and support for audit logging + versioning.

### Decisions (confirmed with user)
- **Primary keys:** UUID for all domain tables (`audit_logs` uses BIGINT — internal, high-volume).
- **Versioning:** hybrid — `version` int columns on agents/tools/reports + a dedicated
  immutable `report_versions` snapshot table; agent/tool config history captured in `audit_logs`.
- **Scope:** documents & citations **deferred** to the ingestion milestone (kept to the 5 named entities).
- **Migration tool:** Alembic.

### Added
- **ORM models** (`app/models/`, SQLAlchemy 2.0 typed style):
  - `base.py` — `Base` + mixins `UUIDPrimaryKeyMixin`, `TimestampMixin`, `SoftDeleteMixin`.
  - `enums.py` — `UserRole`, `ToolCategory`, `JobType`, `JobStatus`, `ReportStatus` (native PG enums).
  - `user.py` (User), `agent.py` (Agent + AgentTool association), `tool.py` (Tool),
    `job.py` (Job), `report.py` (Report + ReportVersion), `audit.py` (AuditLog).
  - `__init__.py` — imports all models so `Base.metadata` sees the full schema.
- **8 tables:** users, agents, tools, agent_tools, jobs, reports, report_versions, audit_logs.
- **Alembic** wired up: `alembic.ini`, `alembic/env.py` (URL from settings, metadata from models),
  `alembic/script.py.mako`, and initial migration
  `alembic/versions/20260719_0001_initial_schema.py` (hand-authored: all enums, tables, FKs, indexes).
- **`tests/test_models.py`** — 4 schema tests (table set, unique email, audit BIGINT pk, report_versions unique).
- Added `alembic==1.14.0` to `requirements.txt`.

### Changed
- **Dockerfile** — also copies `alembic/` and `alembic.ini`.
- **docker-compose.yml** — backend `command` now runs `alembic upgrade head` before uvicorn;
  mounts `./backend/alembic` for dev.
- **WORKING.md** — added schema table, migration commands, workflow convention (design→implement→document).

### Verified (offline — no Postgres needed)
- `pytest` → **7 passed** (3 health + 4 model); mappers configure cleanly.
- `alembic upgrade head --sql` → renders all 8 tables, 5 enum types, indexes, constraints. ✅
- `alembic downgrade --sql` → fully reversible (drops in correct order + enum types). ✅

### Verified (live — real Postgres, 2026-07-19)
- `docker compose up --build` → image built, `mari-db` + `mari-backend` both healthy.
- `alembic upgrade head` auto-ran on start → applied `0001_initial`; **all 8 tables created**
  (confirmed via `psql \dt`: users, agents, tools, agent_tools, jobs, reports, report_versions, audit_logs).
- `/api/v1/health` and `/api/v1/health/db` both returned `200` (DB reachable).

### Notes for next session
- Migrations auto-apply on backend container start.
- If models change: `alembic revision --autogenerate` (needs a live DB), review, commit.
- M2 changes are **not yet committed/pushed** (pending user's go-ahead + PAT).
- Awaiting **Milestone 3** requirements.

---

## [Milestone 1 — Project Setup] — 2026-07-19

**Goal:** Stand up a modular FastAPI backend skeleton with local Docker deployment,
PostgreSQL, and Git, ready for future milestones to build on.

### Decisions
- **Database:** PostgreSQL 16 (chosen over the "MySQL" mention because deliverables
  require a Postgres schema + migrations).
- **Repo layout:** monorepo — `backend/` now, `frontend/` (Angular) later.
- **Dependencies:** pinned `requirements.txt` (not Poetry/uv).
- **Postgres:** runs as a Docker container (no native install required).

### Added
- **Backend app package** (`backend/app/`) with modular structure:
  - `main.py` — FastAPI app factory `create_app()`, lifespan handler, CORS middleware,
    mounts `/api/v1`, auto OpenAPI docs at `/docs`.
  - `core/config.py` — `Settings` via pydantic-settings (single env entry point).
  - `core/logging.py` — `configure_logging()`.
  - `api/v1/router.py` — router aggregator.
  - `api/v1/routes/health.py` — `GET /health` (liveness) and `GET /health/db` (readiness, runs `SELECT 1`).
  - `db/session.py` — SQLAlchemy engine, `SessionLocal`, `get_db()` dependency (no tables yet).
  - `models/base.py` — SQLAlchemy `DeclarativeBase`.
  - `schemas/health.py` — Pydantic response models.
  - `services/` — placeholder for business logic.
- **`backend/tests/test_health.py`** — 3 smoke tests (root, health, OpenAPI schema).
- **`backend/requirements.txt`** — fastapi, uvicorn[standard], pydantic, pydantic-settings,
  python-dotenv, SQLAlchemy, psycopg[binary], pytest, httpx (all pinned).
- **`backend/Dockerfile`** — python:3.12-slim, non-root user, layer-cached deps.
- **`backend/.dockerignore`**.
- **`docker-compose.yml`** (root) — `db` (postgres:16 with healthcheck + `pgdata` volume)
  and `backend` (build, depends_on db healthy, live-reload volume mount + `--reload`).
- **`.env.example`** — documents all env vars.
- **`.gitignore`**, **`.gitattributes`** (LF normalization).
- **`README.md`** — overview, stack table, layout, quick-start, run/test instructions.
- **`.vscode/settings.json`** (git-ignored) — points Pylance at `backend/.venv`.
- **`WORKING.md`** and **`CHANGELOG.md`** — session handoff docs.

### Changed
- Refactored deprecated FastAPI `@app.on_event("startup")` → modern `lifespan` handler
  (removed the deprecation warning; tests clean).
- Resolved README merge conflict during rebase, keeping the detailed project README
  over GitHub's auto-generated one-liner.

### Verified
- `pytest` → **3 passed** (deps installed in `backend/.venv`).
- `docker compose config` → **valid**.
- ⏳ Full `docker compose up` + live `/health/db` — **not yet run** (needs Docker Desktop running).

### Git / GitHub
- `git init`, initial commit, branch `main`.
- Repointed `origin` from an old repo to
  `https://github.com/RPahade/Multi-Agent-Research-Platform`.
- **Push blocked twice, then succeeded:**
  1. 403 — stored credential was for account `rohan-itmtb` (no write access).
  2. 403 — first PAT had **no scopes**.
  3. ✅ Second PAT (with `repo` scope) worked; rebased onto remote's initial commit; pushed.
- Scrubbed the token from `.git/config` (`branch.main.remote` had captured it via `-u`);
  verified `.git/config` is token-free. Reminded user to revoke the exposed token.

### Notes for next session
- Do NOT install Postgres natively — it's containerised.
- Pushing needs a `RPahade` PAT (or fixing the Windows-stored `rohan-itmtb` credential).
- Awaiting **Milestone 2** requirements from the user.
