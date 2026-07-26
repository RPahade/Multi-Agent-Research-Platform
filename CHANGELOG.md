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

## [Milestone 8 — API Documentation] — 2026-07-26

**Goal:** document all backend APIs with request/response examples. (OpenAPI generation and
Swagger/ReDoc exposure were already in place since Milestone 1 — `/docs`, `/redoc`,
`/openapi.json` — so this milestone focused on examples + polish.)

### Added
- **Request/response examples** on every API schema via Pydantic `json_schema_extra`
  (`schemas/{auth,user,agent,tool,report,job,document,health}.py`) — shown in Swagger and
  ReDoc for both request bodies and responses.
- **Named request examples** on `POST /jobs` (`rag_research`, `inline_sources`, `simulated`)
  via `Body(openapi_examples=...)` — a dropdown in Swagger's "Try it out".
- **Enriched OpenAPI metadata** in `main.py`: a full API `description` (auth + typical flow),
  `summary`, `contact`, `license_info`, and `openapi_tags` with per-tag descriptions (10 tags).

### Verified (live)
- `/openapi.json`, `/docs`, `/redoc` all return 200; schema-level `examples` present on
  UserCreate/JobCreate/ReportRead/DocumentRead/HealthResponse/…; `POST /jobs` exposes the 3
  named examples; 10 documented tag groups; test suite 11 passed.

**All 8 backend milestones complete.**

---

## [Milestone 7 — Kafka Integration] — 2026-07-26

**Goal:** local Kafka + event-driven communication (producer from a file, consumer that logs,
event schema with job id/status/timestamp).

### Decisions
- KRaft single broker (no ZooKeeper) + Kafka UI; `confluent-kafka` client;
  file-replay producer AND real backend job events + a consumer service (full integration).

### Added
- **Compose**: `kafka` (`apache/kafka:3.9.0`, KRaft), `kafka-ui` (http://localhost:8085),
  `consumer` (reuses backend image, runs `app.kafka.consumer`). Backend env + `samples/` mount +
  `kafkadata` volume. Broker advertises `kafka:9092` (internal) / `localhost:29092` (host).
- **Event schema** `app/schemas/events.py` — `JobEvent {event_id, event_type, job_id, status,
  progress, current_step, timestamp}`; topic `agent.job.events`, keyed by job_id.
- **Real producer** `app/services/event_publisher.py` — best-effort (KAFKA_ENABLED toggle, lazy
  import, never breaks a job). Wired into the job lifecycle: created / running / progress /
  succeeded / retry / failed / cancelled. Flushed on app shutdown.
- **File-replay producer** `app/kafka/file_producer.py` (reads JSONL, validates, publishes) +
  `samples/job_events.jsonl`.
- **Consumer** `app/kafka/consumer.py` — subscribes and logs each message (partition/offset).
- `GET /api/v1/events/status`; config `KAFKA_ENABLED/BOOTSTRAP_SERVERS/TOPIC/CONSUMER_GROUP`;
  dep `confluent-kafka==2.6.1`.

### Verified (live)
- httpx + docker e2e **all passed**: a research job produced the full ordered event stream
  (created → running → progress×5 for each tool step → succeeded), consumed and logged by the
  consumer with partition/offset; the file-replay producer published 8 events and the consumer
  logged them (including a `job.failed`). `events/status` reflects config.

### Gotchas
- `KAFKA_LISTENERS` must use empty-host binds (`PLAINTEXT://:9092`), not `0.0.0.0` — Kafka
  rejects `0.0.0.0` as a nonroutable advertised address (broker crash-looped until fixed).
- Consumer may log a transient `UNKNOWN_TOPIC_OR_PART` at startup before the topic auto-creates
  on first publish — benign, self-resolves.

**Next:** Milestone 8.

---

## [Milestone 6 — Agent Orchestration] — 2026-07-19/20 (step-by-step)

### Step 4 of 4 — MCP tools ✅ (Milestone 6 COMPLETE)

**Decisions:** move the self-contained tools (research/citation/compliance) to a separate
MCP server over Streamable HTTP; keep retrieval + synthesis local; fall back to local tools
if the MCP server is down; build our own now (extensible to third-party servers later).

**Added:**
- `mcp_server/` — standalone service (container `mari-mcp`, port 8090) using `FastMCP`
  (official `mcp` SDK) exposing `web_research`, `verify_citations`, and `redact_pii`
  (**real regex PII redaction**: email/phone/SSN/card).
- `app/agent/mcp/client.py` — sync wrapper over the async MCP SDK (short-lived
  Streamable-HTTP session per call, timeout, lazy SDK import); `call`, `list_tool_names`, `status`.
- `app/agent/mcp/tools.py` — `MCPTool` + research/citation/compliance adapters (same `Tool`
  interface) that forward to MCP and **fall back to the local tool** on failure.
- `build_pipeline()` wraps those 3 tools when `MCP_ENABLED`; retrieval/synthesis stay local.
- `GET /api/v1/mcp/status`; config `MCP_ENABLED`/`MCP_SERVER_URL`; `mcp>=1.9,<2`; compose `mcp`
  service + backend `depends_on` + env.

**Verified (live):** 14/14 — discovery lists the 3 tools; research/citation/compliance run
`via:"mcp"` (retrieval stays local); real `redact_pii` produced 4 redactions on PII text;
**stopping the MCP container → job still succeeded on local fallback** (`via:"local-fallback"`),
then recovered when restarted.

**Milestone 6 COMPLETE** — single agent orchestrating tools sequentially, real LLM synthesis,
RAG retrieval, and MCP-based tools, with graceful partial-failure handling throughout.
Built entirely in plain Python (no LangChain/LangGraph); Langfuse tracing remains a later milestone.

### Step 3 of 4 — RAG: document ingestion & retrieval ✅

**Decisions:** pgvector in Postgres; Gemini embeddings; originals saved to a mounted volume.

**Added:**
- Migration `0005_documents_rag` — `CREATE EXTENSION vector`; `documents` +
  `document_chunks(embedding vector(768))` with an **HNSW cosine index**; `document_status` enum.
  DB image switched to `pgvector/pgvector:pg16` (existing volume preserved).
- `agent/llm/embeddings.py` — `EmbeddingClient` + Gemini/OpenAI adapters. Gemini
  `gemini-embedding-001` at `outputDimensionality=768` (pgvector indexes cap at 2000 dims),
  **L2-normalized client-side** since truncated Gemini vectors aren't unit-length.
- `services/document_parser.py` (pypdf / python-docx / text) and `services/chunking.py`
  (~1000 chars, 150 overlap, paragraph-aware, page numbers kept for citations).
- `services/document_service.py` (storage, CRUD, **pgvector cosine search**) and
  `services/ingestion_service.py` (parse → chunk → embed in batches of 32 → store), run as an
  **ingestion job** so it reuses M5 progress/cancel/retry/SSE.
- `agent/tools/retrieval.py` replaces the ingestion stub: embeds the query, retrieves top-K
  chunks (optionally filtered by `input.document_ids`), feeds them to synthesis as cited
  sources; falls back to inline `input.sources`.
- `api/v1/routes/documents.py` — upload (multipart, 25 MB cap), list, get, **chunks**, delete.
- **Gemini model failover** (`GEMINI_FALLBACK_MODELS`): 503 "high demand" on one model now
  transparently falls through to the next.
- `samples/vendor_{a,b}_*.txt` for manual testing.

**Verified (live):** uploaded 2 documents → ingestion jobs succeeded → chunked + embedded →
`retrieval` returned 5 chunks (top score 0.73) across 2 documents via vector search (not inline)
→ **grounded, cited report** (EU residency + breach timelines) with `degraded=false`.
Model failover proved out (primary 503 → `gemini-flash-lite-latest`). With `top_k=5` the model
correctly declined a fact absent from the retrieved chunks; `top_k=12` retrieved it and answered
fully — a clean demonstration of retrieval recall tuning.

**Gotchas:** `DocumentChunk.text` shadows SQLAlchemy's `text()` (imported as `sa_text`);
the pgvector image ships an older glibc → ran `ALTER DATABASE research REFRESH COLLATION VERSION`.

**Next step:** step 4 = MCP tools behind the existing `Tool` interface.

### Step 2 of 4 — LLM synthesis ✅

**Decisions:** provider-agnostic (OpenAI + Gemini adapters); grounding via `input.sources`
now; retry then fall back to the deterministic stub on LLM failure.

**Added:**
- `app/agent/llm/` — `LLMClient` interface + `OpenAIClient` + `GeminiClient` (raw httpx,
  no SDK deps), `get_llm_client()` factory (from `LLM_PROVIDER`), `call_with_retry`
  (backoff on 429/5xx/timeout), and `extract_json()` (tolerates code fences / trailing text).
- `app/agent/tools/synthesis.py` — replaces FormattingTool in the pipeline; builds a grounded
  prompt (query + sources + findings), gets a JSON report, records `generated_by`
  (provider/model/usage); **falls back to a stub report** (`content.degraded=true`) if the LLM
  is unavailable, so the job still succeeds.
- Config/env: `LLM_PROVIDER`, `OPENAI_API_KEY`/`OPENAI_MODEL`, `GEMINI_API_KEY`/`GEMINI_MODEL`,
  `LLM_TEMPERATURE`, `LLM_MAX_TOKENS` (+ `.env.example` and compose passthrough).
- Pipeline reordered: `ingestion → research → synthesis → citation → compliance`.

**Verified (live):**
- Fallback path (no key) → stub report, job succeeds (5/5).
- **Real LLM via Gemini `gemini-flash-latest`** → genuine grounded, cited report (6/6),
  ~1.7k tokens, `degraded=false`.
- Real provider errors handled gracefully end-to-end: OpenAI `429 quota exceeded` (no billing)
  and Gemini `404` for retired model names both fell back cleanly.

**Gotchas documented:** LLM model names are key-specific and change (`gemini-1.5/2.5-flash`
404'd; `gemini-flash-latest` works — now the default); `docker compose up -d` (not `restart`)
is required to load `.env` changes; LLMs emit trailing text even in JSON mode (handled by
`extract_json`).

**Next steps:** step 3 = RAG (upload/parse docs → chunk → embed → retrieve); step 4 = MCP tools.

### Step 1 of 4 — sequential tool pipeline (own Python tools) + partial failures ✅

**Decisions:** plain Python first (no framework/LLM/MCP yet); per-step results in a
`job_steps` table; per-tool required/optional failure policy; pipeline produces a Report.

**Added:**
- `app/agent/base.py` — `Tool` ABC (`key/name/required`, `run(ctx)`), `ToolContext`
  (threads `input` + `artifacts`), `ToolResult`. *This is the interface MCP will implement later.*
- `app/agent/tools/` — 5 deterministic stub tools (ingestion, research, citation[optional],
  formatting, compliance) + `build_pipeline()`.
- `app/agent/orchestrator.py` — runs the pipeline sequentially inside a job: records each tool
  as a `job_steps` row, updates progress/current_step (conditional; cancel-aware), applies the
  required/optional failure policy, and writes/updates the job's Report.
- Migration `0004_job_steps` + `JobStep` model + `JobStepStatus` enum; `GET /jobs/{id}/steps`
  endpoint + `JobStepRead` schema.
- `job_service`: `is_running`, `set_progress` (shared conditional update), `list_steps`.
- `job_runner`: `type=research` now delegates to the orchestrator; the simulated pipeline
  remains for non-research types.

**Verified (live):** httpx e2e **17/17 passed** — happy path (5 steps in order, report linked
to job), optional-tool failure (job still succeeds, report has warnings), required-tool failure
(pipeline stops, job failed, no report), cancel mid-orchestration, and M5 simulated pipeline
still works via `type=export`. Data kept.

**Behavior note:** `type=research` = real orchestration; the old simulated pipeline
(`steps`/`step_seconds`/`fail`) now runs for non-research job types only.

**Next steps:** step 2 = Claude LLM synthesis; step 3 = RAG ingestion; step 4 = MCP tools.

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
