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

## [Milestone 5 — Background Task Execution] — 2026-07-19 (step-by-step)

### Step 1 of 3 — job creation, progress tracking, cancellation ✅

**Decisions:** in-process `ThreadPoolExecutor` (swap to a queue/Kafka in a later step);
create/cancel = analyst+admin, read = any auth. No migration (reuses M2 `jobs` table).

**Added:**
- `services/job_runner.py` — thread-pool runner; simulated multi-step pipeline (placeholder
  for the real agent); DB-driven progress; **cooperative cancellation** via conditional
  updates (`WHERE status='running'`) so cancelled jobs aren't resurrected; params
  `steps/step_seconds/fail/fail_step` in `job.input`. `submit()` + `shutdown()`.
- `services/job_service.py` — `create_job`, `get_job`, `list_page` (filter status/type),
  `request_cancel` (atomic pending/running → cancelled).
- `schemas/job.py` (JobCreate, JobRead); `api/v1/routes/jobs.py`
  (`POST /jobs`, `GET /jobs`, `GET /jobs/{id}`, `POST /jobs/{id}/cancel`); `require_job_writer` dep.
- `main.py` lifespan shuts the executor down on app stop.

**Verified (live):** httpx e2e **13/13 passed** — async create (pending→running→succeeded,
progress 100), cancel a running job (stays cancelled, progress<100), 409 cancelling a finished
job, simulated failure path with error, leadership create→403, status filter, unknown→404.
Test data **kept** in DB (no cleanup from M5 onward).

### Step 2 of 3 — idempotency + resilience to failures ✅

**Decisions:** auto-retry with default `max_attempts=3`; reaper + startup recovery.

**Added:**
- Migration `0003_job_resilience` — `jobs.idempotency_key`, `attempts`, `max_attempts`,
  `last_heartbeat`; unique partial index `(user_id, idempotency_key)`.
- **Idempotency**: `Idempotency-Key` header on `POST /jobs` returns the existing job (200)
  on repeat; `IntegrityError` on a concurrent race also returns the winner.
- **Retries**: `job_runner` increments `attempts` on each run; `_fail_or_retry` requeues a
  failed run until `attempts == max_attempts`, then marks `failed`. Simulated `fail_times`
  param lets a job fail then converge.
- **Startup recovery**: `recover_orphans()` (called in lifespan) requeues jobs left `running`
  (crashed) or `pending`, or fails them if out of attempts.
- **Reaper**: `start_reaper()` background thread requeues `running` jobs with a stale
  `last_heartbeat` (defaults: interval 10s, stale 30s). `stop_reaper()` on shutdown.
- Config: `default_max_attempts`, `job_reaper_interval_seconds`, `job_heartbeat_stale_seconds`.

**Verified (live):** httpx e2e **15/15 passed** — idempotent dedup (same id, 200), retries
converge (fail×2 → succeeded, attempts=3), retries exhaust (failed at attempts=2),
**reaper** recovers a forced stale-running job, and **startup recovery** after a real
`docker compose kill` (SIGKILL) re-runs the orphaned job to success (attempts=2).
Data kept in DB.

### Step 3 of 3 — live status updates for running jobs ✅

**Decision:** Server-Sent Events (SSE) for one-way status push; no new deps; Kafka can back it later.

**Added:**
- `GET /jobs/{id}/stream` (`api/v1/routes/jobs.py`) — SSE `text/event-stream`. Async generator
  emits `{id,status,progress,current_step,attempts,error}` on each change, `: ping` keep-alive
  when idle, and closes on terminal status. Uses `asyncio.to_thread` + short-lived sessions;
  respects client disconnect; 600s safety cap. 404 if the job doesn't exist.

**Verified (live):** streamed a running job end-to-end — received multiple events, progress
advanced monotonically to 100, final event `succeeded`.

**Milestone 5 COMPLETE** (all 3 steps). Not yet wired: Kafka event bus (separate deliverable).

### Full regression — Milestone 1 → 5 (2026-07-19)
Single httpx e2e suite, **49/49 passed**:
- **M1** (4): health, health/db, root, OpenAPI.
- **M3** (9): admin login, wrong-password 401, /me, no-token 401, refresh rotation (old→401),
  logout revocation, analyst/leadership login.
- **M4** (22): pagination envelope + size, filters, analyst→/users 403, user PATCH/soft-delete/404,
  agent RBAC + version bump, tool unique-key 409 + filter, report RBAC + version snapshots,
  422 validation, 404.
- **M5 step 1** (5): async create→succeeded(100%), cancel running, 409 on finished, failure path.
- **M5 step 2** (4): idempotency dedup, retries converge (attempts=3) & exhaust (failed), reaper recovery.
- **M5 step 3** (5): SSE 200 text/event-stream, multiple events, monotonic progress→100, terminal event.
- (SIGKILL crash recovery validated separately in the step-2 run.)

---

## [Milestone 4 — CRUD APIs] — 2026-07-19

**Goal:** REST CRUD for core entities with pagination, filtering, validation, graceful errors.

### Decisions
- **RBAC (role-appropriate):** users admin-only; agents/tools reads any-auth, writes admin;
  reports reads any-auth, writes analyst+admin (leadership read-only).
- **Report updates snapshot** the new state into report_versions and bump `version`.
- Pagination = `page/size` envelope; DELETE = soft-delete; audit-log writes deferred to observability milestone.

### Added
- `schemas/common.py` — `PageParams` (query dep) + generic `Page[T]` envelope.
- `services/crud.py` — `paginate(stmt)` (count + limit/offset).
- `app/api/utils.py` — `get_active_or_404` (soft-delete aware).
- Schemas: `agent.py`, `tool.py`, `report.py` (Create/Update/Read + `ReportVersionRead`); `user.py` gains `UserUpdate`.
- Services: `agent_service`, `tool_service`, `report_service` (CRUD + filters; report version snapshots);
  `user_service` gains `list_users_page`, `update_user`, `soft_delete_user`.
- Routes: full CRUD for `users` (admin-only, extended from M3), `agents`, `tools`, `reports`
  (+ `GET /reports/{id}/versions`). New dep `require_report_writer` (admin+analyst).
- 204 delete handlers return an explicit empty `Response` (FastAPI disallows a body on 204).

### Verified (live — real Postgres, 2026-07-19)
- `pytest` → **11 passed** (no schema change; code hot-reloaded via mounted volume).
- End-to-end httpx CRUD flow (**25 checks, all passed**): paginated envelope + size honored,
  role/category/status filters, admin-only users (analyst 403), agent write 403 for analyst,
  version bump on agent/report update, duplicate tool key 409, leadership report-create 403,
  report version history (v1 preserved, v2 current), soft-delete then 404, missing field 422.
- Test data cleaned up afterward (only seeded admin remains).

### Notes for next session
- No new migration in M4 (used existing M2 schema). New entity code follows the
  service/schema/route split — reuse `Page[T]`, `paginate`, `get_active_or_404` for new entities.

---

## [Milestone 3 — Authentication & RBAC] — 2026-07-19

**Goal:** Secure JWT authentication (access + refresh) with role-based access control.

### Decisions
- **Roles:** keep 3-role enum (analyst/admin/leadership); RBAC enforces admin vs others.
- **User creation:** admin-only (`POST /users`); first admin seeded from env on startup.
- **Libraries:** PyJWT (tokens), bcrypt (hashing, direct — no passlib), python-multipart, email-validator.

### Added
- `app/core/security.py` — bcrypt password hash/verify; JWT create/decode for access &
  refresh tokens (access carries `sub`+`role`; both carry `jti`+`exp`+`type`).
- `app/models/refresh_token.py` + migration `0002_refresh_tokens` — tracks issued refresh
  tokens (`jti` unique, `expires_at`, `revoked_at`) for rotation & logout.
- `app/services/user_service.py` — get/create/list users + `seed_first_admin`.
- `app/services/auth_service.py` — `authenticate`, `issue_token_pair`,
  `rotate_refresh_token` (revoke-old-issue-new), `logout` (revoke jti).
- `app/api/deps.py` — `get_current_user` (OAuth2 bearer), `require_roles(...)`, `require_admin`.
- Routes: `auth.py` (`POST /auth/login|refresh|logout`, `GET /auth/me`) and
  `users.py` (`GET/POST /users`, admin-only).
- Schemas: `schemas/auth.py` (TokenPair, RefreshRequest), `schemas/user.py` (UserCreate, UserRead).
- Config: JWT + first-admin settings; `.env.example` and docker-compose env updated.
- Startup: `main.py` lifespan seeds the first admin (best-effort).
- Tests: `tests/test_security.py` (4 unit tests, no DB).

### Verified (live — real Postgres, 2026-07-19)
- `pytest` → **11 passed**. Migrations `0001`→`0002` applied on container start; `refresh_tokens`
  created; admin `admin@example.com` seeded.
- End-to-end httpx flow (15 checks, **all passed**): admin login, wrong-password 401, `/me`,
  no-token 401, admin list/create users, duplicate-email 409, analyst login,
  **analyst→/users 403 (RBAC)**, refresh rotation (old token 401), logout (revoked token 401).
- Test data cleaned up afterward (only seeded admin remains).

### Notes for next session
- Change `JWT_SECRET_KEY` + admin password for any non-dev use.
- Reuse `Depends(get_current_user)` / `Depends(require_admin)` to protect future endpoints.

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
