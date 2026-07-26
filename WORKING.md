# WORKING.md — Project State & Session Handoff

> **Purpose:** Single source of truth for the current state of this project.
> A new session (or new developer) should read this file **first** to understand
> what exists, why, how to run it, and what to do next.
> Pair with [CHANGELOG.md](CHANGELOG.md), which logs *what changed and when*.

_Last updated: 2026-07-19 (end of Milestone 1)._

---

## 1. What this project is

**Multi-Agent Research Intelligence Platform** — a research agent platform for
Procurement & Strategy teams. It ingests large documents (PDF, DOCX), performs web
and internal research via configurable tools, synthesises **cited** reports, enables
interactive **chat with the evidence**, and produces **auditable logs** for compliance.

**Core concept:** one orchestrating **Agent** that drives a toolbox of 5 tools:
1. Document ingestion & retrieval
2. Web research
3. Citation verification
4. Formatting & exporting (DOCX/PDF)
5. Compliance (PII redaction)

**Cross-cutting requirements:** long-running tasks run **asynchronously**; live status
**streams** to the UI; **role-based access** (Analyst / Admin / Leadership); security,
reliability, observability.

---

## 2. Tech stack (confirmed decisions)

| Layer         | Choice                          | Notes |
|---------------|---------------------------------|-------|
| Backend       | FastAPI (Python 3.12)           | modular structure |
| Database      | **PostgreSQL 16**               | Decided over MySQL: deliverables require a Postgres schema. Runs as a Docker container — **no native install needed**. |
| Messaging     | Kafka (local)                   | *not yet built* — later milestone |
| Observability | Langfuse                        | *not yet built* — later milestone |
| Frontend      | Angular                         | *not yet built* — later milestone |
| Infra         | Docker + docker-compose         | local deployment |
| Dependencies  | `requirements.txt` (pinned)     | in `backend/` |
| Repo layout   | **Monorepo**: `backend/` now, `frontend/` later | |

---

## 3. Milestone roadmap (Backend = 8 milestones)

- [x] **Milestone 1 — Project Setup** ✅ DONE (see below + CHANGELOG)
- [x] **Milestone 2 — Database Design** ✅ DONE (schema + models + migration; verified live)
- [x] **Milestone 3 — Authentication & RBAC** ✅ DONE (JWT access+refresh, roles, logout; verified live)
- [x] **Milestone 4 — CRUD APIs** ✅ DONE (users/agents/tools/reports CRUD, pagination, filtering, versioning; verified live)
- [x] **Milestone 5 — Background Task Execution** ✅ DONE — all 3 steps, verified live:
  - [x] step 1/3: job creation, progress tracking, cancellation
  - [x] step 2/3: idempotency + resilience (retries, startup recovery, reaper)
  - [x] step 3/3: live status updates via SSE
- [~] **Milestone 6 — Agent Orchestration** 🚧 IN PROGRESS (step-by-step, plain Python first):
  - [x] step 1: sequential tool pipeline (own Python tools) + partial-failure handling ✅
  - [x] step 2: LLM synthesis (OpenAI + Gemini adapters, grounded+cited, stub fallback) ✅ verified live with **Gemini** (`gemini-flash-latest`)
  - [x] step 3: RAG ✅ upload → parse → chunk → embed (Gemini) → pgvector cosine retrieval → cited report
  - [ ] step 4: MCP-based tools (same Tool interface)
- [ ] Milestone 7–8 — *(awaiting details)*

> The user provides milestone requirements one at a time. Do **not** build ahead of
> the current milestone. Ask for the next milestone's details when the current is done.

### Workflow convention (per milestone)
1. **Design first** — propose the design, confirm key decisions with the user, get sign-off.
2. **Then implement** — build against the agreed design.
3. **Then document** — update WORKING.md + CHANGELOG.md at the end of the milestone.
4. **Commit once the milestone is complete** — not after each step (user preference).
   Large milestones are built step-by-step, but all steps land in one commit at the end.

---

## 4. Current state — what EXISTS right now (after Milestone 1)

A runnable, modular FastAPI backend skeleton + PostgreSQL, containerised, committed
and pushed to GitHub. **No business logic yet** — just the foundation.

### Folder structure
```
d:\Multiagent\
├── WORKING.md                 # this file
├── CHANGELOG.md               # change log
├── README.md                  # user-facing setup guide
├── docker-compose.yml         # backend + postgres:16
├── .env.example               # env template (copy to .env)
├── .env                        # local, git-ignored
├── .gitignore / .gitattributes
├── .vscode/settings.json      # git-ignored; points Pylance at backend/.venv
├── backend/
│   ├── Dockerfile             # python:3.12-slim, non-root
│   ├── .dockerignore
│   ├── requirements.txt       # + alembic (M2)
│   ├── alembic.ini            # Alembic config (DB url injected from settings)
│   ├── alembic/               # migrations
│   │   ├── env.py             # uses app.models Base.metadata + settings.database_url
│   │   ├── script.py.mako
│   │   └── versions/
│   │       └── 20260719_0001_initial_schema.py   # creates all tables/enums/indexes
│   ├── .venv/                 # git-ignored local virtualenv (deps installed here)
│   ├── app/
│   │   ├── main.py            # app factory create_app(); lifespan; CORS; mounts /api/v1; OpenAPI at /docs
│   │   ├── core/
│   │   │   ├── config.py      # Settings (pydantic-settings) — ONLY place env is read
│   │   │   └── logging.py     # configure_logging()
│   │   ├── api/v1/
│   │   │   ├── router.py      # aggregates routers (include new feature routers here)
│   │   │   └── routes/health.py  # GET /health (liveness), GET /health/db (readiness)
│   │   ├── db/session.py      # engine + SessionLocal + get_db() dependency
│   │   ├── models/            # SQLAlchemy ORM (M2)
│   │   │   ├── base.py        # Base + mixins: UUIDPrimaryKey, Timestamp, SoftDelete
│   │   │   ├── enums.py       # UserRole, ToolCategory, JobType, JobStatus, ReportStatus
│   │   │   ├── user.py        # User
│   │   │   ├── agent.py       # Agent + AgentTool (association)
│   │   │   ├── tool.py        # Tool
│   │   │   ├── job.py         # Job
│   │   │   ├── report.py      # Report + ReportVersion (snapshots)
│   │   │   └── audit.py       # AuditLog (append-only, BIGINT pk)
│   │   ├── schemas/health.py  # Pydantic response models
│   │   └── services/          # business logic (empty placeholder)
│   └── tests/
│       ├── test_health.py     # 3 smoke tests (root, health, openapi)
│       └── test_models.py     # 4 schema tests (tables, constraints) — no DB needed
```

### Endpoints available
- `GET /` → service metadata + docs link
- `GET /api/v1/health` → `{status:"ok", app, version, env}` (liveness, no DB)
- `GET /api/v1/health/db` → `{status:"ok", database:"reachable"}` (runs `SELECT 1`)
- **Auth (M3):** `POST /api/v1/auth/login` · `POST /auth/refresh` · `POST /auth/logout` · `GET /auth/me`
- **CRUD (M4):** `/api/v1/{users,agents,tools,reports}` — `GET` (list, paginated+filtered), `GET /{id}`, `POST`, `PATCH /{id}`, `DELETE /{id}` (soft). Plus `GET /reports/{id}/versions`.
- **Jobs (M5):** `POST /api/v1/jobs` (async; optional `Idempotency-Key` header dedups), `GET /jobs` (list/filter), `GET /jobs/{id}` (status+progress+attempts), `POST /jobs/{id}/cancel`, `GET /jobs/{id}/stream` (**SSE** live status).
- **Jobs orchestration (M6):** `GET /jobs/{id}/steps` — per-tool orchestration trace (status/output/error per tool).
- `GET /docs` → Swagger UI (use "Authorize" with a token) · `GET /redoc` · `GET /openapi.json`

### Conventions established (follow these in future milestones)
- **Config:** read env ONLY via `app/core/config.py` (`from app.core.config import settings`). Never `os.environ` elsewhere.
- **New routes:** create `app/api/v1/routes/<feature>.py` with an `APIRouter`, then include it in `app/api/v1/router.py`.
- **DB access:** inject `Depends(get_db)` from `app/db/session.py`.
- **ORM models:** inherit `Base` from `app/models/base.py`.
- **Schemas:** Pydantic request/response models go in `app/schemas/`.
- **Business logic:** goes in `app/services/`, kept out of route handlers.
- **DB changes:** edit models → `alembic revision --autogenerate -m "..."` → review → commit. Never hand-edit applied migrations.

### Database schema (Milestone 2)
8 tables. Decisions: **UUID PKs** (audit_logs uses BIGINT), **hybrid versioning**, documents/citations **deferred**.

| Table | Purpose | Key points |
|-------|---------|-----------|
| `users` | login + RBAC | `role` enum (analyst/admin/leadership); `hashed_password` (auth later); soft-delete |
| `agents` | orchestrating agent config | `system_prompt`, `model`, `config` JSONB, `version`; `created_by`→users |
| `tools` | the 5 configurable tools | `key` unique, `category` enum, `config` JSONB, `enabled`, `version` |
| `agent_tools` | which tools an agent may use | composite PK (agent_id, tool_id), `config_override` |
| `jobs` | long-running async tasks | `type`/`status` enums, `input` JSONB, `progress`+`current_step` (for streaming), timestamps |
| `reports` | generated cited reports | `content` JSONB, `status` enum, `version`; 1:1 with a job (`job_id` unique) |
| `report_versions` | immutable report snapshots | unique (report_id, version); versioning history |
| `audit_logs` | append-only compliance trail | BIGINT pk; actor/action/entity, `changes` JSONB, `trace_id` (Langfuse), `ip_address` |

- **Versioning** = `version` int on agents/tools/reports + `report_versions` snapshots; agent/tool config history captured in `audit_logs`.
- **Audit logging** = the `audit_logs` table, never updated/deleted.
- Migrations run automatically on backend container start (`alembic upgrade head` in the compose command).

### Authentication & RBAC (Milestone 3)
- **JWT**: access token (30 min, stateless, carries `sub`+`role`) + refresh token (7 days, `jti` tracked in `refresh_tokens`).
- **Password hashing**: bcrypt (`app/core/security.py`); tokens via PyJWT.
- **Refresh rotation**: `/auth/refresh` revokes the presented token and issues a new pair. **Logout** revokes the refresh token's `jti`. Access tokens are not revocable — they just expire.
- **Roles**: `analyst` / `admin` / `leadership`. RBAC via `require_roles(...)` / `require_admin` in `app/api/deps.py`.
- **First admin**: seeded on startup from `FIRST_ADMIN_EMAIL`/`FIRST_ADMIN_PASSWORD` (dev default `admin@example.com` / `ChangeMe123!`). User creation is **admin-only** (`POST /users`).
- **Key files**: `core/security.py`, `api/deps.py`, `services/auth_service.py`, `services/user_service.py`, `api/v1/routes/{auth,users}.py`, `models/refresh_token.py`.
- ⚠️ **Change `JWT_SECRET_KEY` and the admin password in any real environment.**

**Auth conventions (reuse in later milestones):**
- Protect an endpoint: `user = Depends(get_current_user)`.
- Restrict by role: `Depends(require_admin)` or `Depends(require_roles(UserRole.ADMIN, UserRole.LEADERSHIP))`.

### CRUD APIs (Milestone 4)
- Full REST CRUD for **users, agents, tools, reports** under `/api/v1/...`. `DELETE` is **soft** (sets `deleted_at`).
- **Pagination**: `?page=&size=` → `Page[T]` envelope `{items,total,page,size,pages}` (`schemas/common.py`); `services/crud.paginate` does the count+limit/offset.
- **Filtering**: users `role/is_active/q`; agents `is_active/q`; tools `category/enabled/q`; reports `status/job_id/q`. Default sort newest-first.
- **RBAC**: users = admin-only (router-level `dependencies=[Depends(require_admin)]`); agents/tools reads = any auth, writes = admin; reports reads = any auth, writes = analyst+admin (`require_report_writer`), leadership read-only.
- **Errors**: `get_active_or_404` (`app/api/utils.py`) → 404; duplicate email/key/job → 409; Pydantic → 422.
- **Report versioning**: create writes a v1 snapshot; each `PATCH` bumps `reports.version` and writes a matching `report_versions` row. `GET /reports/{id}/versions` lists history.
- **Conventions**: entity service in `services/<entity>_service.py` (returns `(items,total)` for lists); Pydantic Create/Update/Read in `schemas/<entity>.py`; thin routers in `api/v1/routes/<entity>.py`.

### Background jobs (Milestone 5 — steps 1–2 of 3 done)
- **Execution**: in-process `ThreadPoolExecutor` in `app/services/job_runner.py` (4 workers). `POST /jobs` inserts a `pending` job and calls `job_runner.submit(id)` — returns immediately; work runs in a background thread. Executor + reaper shut down on app shutdown (lifespan).
- **Job body**: a *simulated* multi-step pipeline (placeholder for the real agent). Tunable via `input`: `steps` (int), `step_seconds` (float), `fail` (bool), `fail_times` (int), `fail_step` (int).
- **Progress/status**: worker writes `status` (pending→running→succeeded/failed/cancelled), `progress` 0–100, `current_step`, `started_at`/`finished_at`, `error`, `last_heartbeat`. Read via `GET /jobs/{id}`.
- **Cancellation**: `POST /jobs/{id}/cancel` sets `status=cancelled` (pending→never starts; running→stops at next step checkpoint). All progress writes are **conditional** (`WHERE status='running'`) so a cancelled job is never resurrected. Cancelling a terminal job → 409.
- **Idempotency (step 2)**: optional `Idempotency-Key` header on `POST /jobs`. Repeat key returns the existing job (200) — de-duped via unique `(user_id, idempotency_key)`.
- **Resilience (step 2)**:
  - **Retries**: `attempts`/`max_attempts` (default 3). A failed run requeues until attempts hit max, then stays `failed`. Attempt count increments on each pending→running transition.
  - **Startup recovery**: on boot, `recover_orphans()` requeues jobs left `running` (crashed process) or `pending`, or fails them if out of attempts.
  - **Reaper**: background thread (`start_reaper`) requeues `running` jobs whose `last_heartbeat` is older than `JOB_HEARTBEAT_STALE_SECONDS` (default 30s; interval 10s) — covers a worker that died in a still-alive process.
- **Config**: `DEFAULT_MAX_ATTEMPTS`, `JOB_REAPER_INTERVAL_SECONDS`, `JOB_HEARTBEAT_STALE_SECONDS` in `core/config.py`.
- **Migration**: `0003_job_resilience` added `idempotency_key`, `attempts`, `max_attempts`, `last_heartbeat`.
- **RBAC**: create/cancel = analyst+admin (`require_job_writer`); read = any authenticated.
- **Live status streaming (step 3)**: `GET /jobs/{id}/stream` returns **Server-Sent Events** (`text/event-stream`). Emits `{id,status,progress,current_step,attempts,error}` on each change, `: ping` keep-alive when idle, closes on terminal status. Implemented with an async generator + `asyncio.to_thread` short-lived DB reads (no new deps). Angular: consume with `EventSource`. Kafka can back this later without changing the client contract.
- **Key files**: `services/job_runner.py`, `services/job_service.py`, `schemas/job.py`, `api/v1/routes/jobs.py`.

> **Migrations don't auto-apply on hot-reload** (only on container start). After adding a migration, run `docker compose restart backend` (re-runs `alembic upgrade head`) or `docker compose exec backend alembic upgrade head`.

### Agent orchestration (Milestone 6 — step 1 of 4 done)
- **The agent = a sequential tool pipeline run inside a job.** For `type=research` jobs, `job_runner` calls `app/agent/orchestrator.py` instead of the simulated pipeline. Each tool becomes a step → updates `current_step`/`progress` (visible via SSE) and is recorded as a `job_steps` row.
- **Tool contract** (`app/agent/base.py`): `Tool{key,name,required}` + `run(ctx) -> ToolResult`. `ToolContext` threads `input` + `artifacts` between tools. **This is the seam MCP plugs into later** — an `MCPTool` will implement the same interface with zero orchestrator changes.
- **Pipeline** (`app/agent/tools/`): `ingestion → research → synthesis → citation → compliance` (`build_pipeline()`). Step 1 tools are deterministic stubs; **synthesis is LLM-powered (step 2)**. (`formatting.py` retained for the future export milestone, not in the pipeline.)

#### LLM synthesis (step 2)
- **Provider-agnostic** `LLMClient` in `app/agent/llm/` (`base.py` + `openai_client.py` + `gemini_client.py`, raw httpx — no SDK deps). `get_llm_client()` picks the provider from `LLM_PROVIDER` (`openai`/`gemini`/`none`).
- **SynthesisTool** builds a grounded prompt (query + `input.sources=[{title,text}]` + research findings), asks the LLM for a JSON report (title/summary/sections/citations), normalizes it, and records `generated_by` (provider/model/usage).
- **Retry + fallback**: transient errors (429/5xx/timeout) retry with backoff; if no provider/key or it keeps failing, it **falls back to a deterministic stub report** (`content.degraded=true`) so the job still succeeds.
- **Config/env**: `LLM_PROVIDER`, `OPENAI_API_KEY`/`OPENAI_MODEL`, `GEMINI_API_KEY`/`GEMINI_MODEL`, `LLM_TEMPERATURE`, `LLM_MAX_TOKENS`. Keys live in `.env` (git-ignored); to switch providers/models, edit `.env` and run **`docker compose up -d`** (recreates the container — a plain `restart` does NOT re-read `.env`).
- **Robust parsing**: `extract_json()` (`llm/base.py`) strips ``` fences and tolerates trailing text (LLMs emit extra data even in JSON mode).
- **Model-name gotcha**: provider model names change and are key-specific. `gemini-1.5-flash` / `gemini-2.5-flash` returned 404 ("not available to new users") for the test key; **`gemini-flash-latest`** worked (now the default). List a key's models: `curl "https://generativelanguage.googleapis.com/v1beta/models?key=KEY"`. OpenAI's test key returned `429 quota exceeded` (needs billing) → the graceful fallback kicked in.
- **Verified live (Gemini `gemini-flash-latest`)**: real grounded, cited report generated (not fallback), ~1.7k tokens.
- **Key files**: `app/agent/llm/*`, `app/agent/tools/synthesis.py`.
- **Partial-failure policy**: `required` tool fails → pipeline stops, job `failed` (steps recorded); `optional` tool fails (currently only `citation`) → recorded and pipeline continues, job `succeeds` with `warnings`.
- **Output**: the pipeline writes a **Report** linked to the job (`report.job_id`); a retry updates it (bumping the report version).
- **`job_steps` table** (migration `0004`): one row per tool — `sequence`, `tool_key`, `status`, `output` JSONB, `error`, timings. Read via `GET /jobs/{id}/steps`.
- **Test hooks** in `job.input`: `fail_tool` (force a tool to fail), `tool_seconds` (per-tool delay), plus `query`/`documents`.
- ⚠️ **Behavior change**: `type=research` now runs real orchestration. The old **simulated** pipeline (`steps`/`step_seconds`/`fail`/`fail_times`) now only runs for **non-research** job types (`export`/`ingestion`) — use those to exercise M5 simulated mechanics.
- **Not done yet**: step 4 = MCP tools. (Langfuse tracing + LangGraph are separate/optional.)

### RAG — documents & retrieval (Milestone 6, step 3) ✅
- **Pipeline is now**: `retrieval → research → synthesis → citation → compliance`.
- **Ingestion flow**: `POST /documents` (multipart) saves the file to the `./data/uploads` volume, creates a `documents` row, and starts an **ingestion job** (`JobType.INGESTION`) — so it inherits M5 progress/cancel/retry/SSE. The job parses (pypdf / python-docx / text), chunks (~1000 chars, 150 overlap, paragraph-aware), embeds in batches of 32, and stores `document_chunks`. Status: uploaded → processing → ingested/failed.
- **Retrieval flow**: `RetrievalTool` embeds the query and runs **pgvector cosine search** (`embedding.cosine_distance`, HNSW index) over ingested chunks, optionally filtered by `input.document_ids`; results become the `sources` synthesis cites. Falls back to inline `input.sources` if no embeddings/matches.
- **Embeddings**: `app/agent/llm/embeddings.py` — `EmbeddingClient` + Gemini/OpenAI adapters. Gemini `gemini-embedding-001` with `outputDimensionality=768`; **vectors are L2-normalized client-side** (truncated Gemini vectors are not unit-length, which would skew cosine).
- **pgvector**: db image is `pgvector/pgvector:pg16`; migration 0005 runs `CREATE EXTENSION vector`, creates `documents` + `document_chunks(embedding vector(768))` + an HNSW cosine index. **Index limit is 2000 dims** — that's why we request 768 instead of the native 3072.
- **Endpoints**: `POST /documents`, `GET /documents`, `GET /documents/{id}`, `GET /documents/{id}/chunks` (inspect what RAG searches), `DELETE /documents/{id}`. Upload/delete = analyst+admin; reads = any auth. 25 MB upload cap.
- **Model failover**: `GEMINI_FALLBACK_MODELS` — Gemini often 503s a specific model ("high demand"); the client retries then transparently tries the next model. Verified live (primary 503 → `gemini-flash-lite-latest` served it).
- **Tuning lesson**: `top_k` governs recall. With `top_k=5` the model correctly said a fact "isn't in the sources"; with `top_k=12` it retrieved the missing clause and answered fully. Default `RETRIEVAL_TOP_K=5`, overridable per job via `input.top_k`.
- **Sample docs**: `samples/vendor_a_proposal.txt`, `samples/vendor_b_contract.txt` for manual testing.
- **Key files**: `models/document.py`, `services/{document_service,ingestion_service,document_parser,chunking}.py`, `agent/tools/retrieval.py`, `agent/llm/embeddings.py`, `api/v1/routes/documents.py`.

> **Gotcha**: `DocumentChunk` has a column named `text`, which shadows SQLAlchemy's `text()` inside the class body — `document.py` imports it as `sa_text`.
- **Key files**: `app/agent/base.py`, `app/agent/tools/*`, `app/agent/orchestrator.py`, `models/job_step.py`, `services/job_runner.py` (research branch).

---

## 5. How to run

**Prerequisite:** Docker Desktop running. (Postgres is a container — nothing to install natively.)

```bash
cd d:\Multiagent
cp .env.example .env          # first time only (already done locally)
docker compose up --build     # first run, or after changing requirements.txt / Dockerfile
# then open http://localhost:8000/docs
```

Day-to-day (code auto-reloads via mounted volume + uvicorn --reload):
| Task | Command |
|------|---------|
| Start (no dep changes) | `docker compose up` (add `-d` for background) |
| Editing .py files | nothing — save and it auto-reloads |
| Logs (background) | `docker compose logs -f backend` |
| Stop | `Ctrl+C` or `docker compose down` |
| Reset DB too | `docker compose down -v` |

Run tests (without Docker):
```bash
cd backend
./.venv/Scripts/python.exe -m pytest        # Windows venv
```

Migrations (Alembic; run from `backend/`, or via `docker compose exec backend ...`):
```bash
alembic upgrade head                         # apply all (auto-runs on container start)
alembic downgrade -1                          # roll back one
alembic revision --autogenerate -m "msg"     # after changing models (needs a live DB)
alembic upgrade head --sql                    # render SQL without a DB (offline check)
```

---

## 6. Verification status

| Check | Result |
|-------|--------|
| `pytest` (in backend/.venv) | ✅ 11 passed (3 health + 4 model + 4 security) |
| `alembic` migrations 0001+0002 (offline render) | ✅ valid & reversible |
| Full `docker compose up --build` (live) | ✅ built, both containers healthy |
| Live migrations `0001`→`0002` on start | ✅ all 9 tables created (incl. `refresh_tokens`) |
| Live admin seed on start | ✅ `admin@example.com` created (admin role) |
| Live auth flow (httpx e2e, 15 checks) | ✅ **ALL PASSED** — login, /me, RBAC 403, refresh rotation, logout revocation |
| Live CRUD flow (httpx e2e, 25 checks) | ✅ **ALL PASSED** — pagination, filtering, RBAC per role, soft-delete, 404/422, report version snapshots |
| Live jobs flow — M5 step 1 (httpx e2e, 13 checks) | ✅ **ALL PASSED** — async create, progress→100, cancel (not resurrected), 409 on finished, failure path, RBAC 403, filter, 404 |
| Live jobs resilience — M5 step 2 (httpx e2e, 15 checks) | ✅ **ALL PASSED** — idempotency dedup, retries converge (attempts=3) & exhaust (failed), reaper recovers stale job, **hard-crash (SIGKILL) startup recovery** |
| **Full M1→M5 regression (httpx e2e, 49 checks)** | ✅ **49/49 PASSED** — health, auth+RBAC, CRUD, jobs, resilience, **SSE stream** |
| Live agent orchestration — M6 step 1 (httpx e2e, 17 checks) | ✅ **ALL PASSED** — 5-tool pipeline in order, per-tool steps, report linked to job, optional-fail continues, required-fail stops (no report), cancel, M5 simulated still works |
| Live `/api/v1/health/db` | ✅ `200` (DB reachable) |

> Note: from M5 on, e2e test data is **kept** in the DB (not cleaned up) for further testing.
| Git commit + push to GitHub | ✅ M1 done; ⏳ M2 not yet committed/pushed |

**DBeaver / psql access:** connect to `localhost:5432`, db `research`, user/pass `postgres`/`postgres`.
Tables live under `research → Schemas → public → Tables` (only while containers run; `pgdata` volume persists data).

---

## 7. Git / GitHub

- **Remote:** `origin` → https://github.com/RPahade/Multi-Agent-Research-Platform (clean URL, no token stored)
- **Branch:** `main`
- **Commit author identity:** `RPahade <rohpahade2@gmail.com>`
- Pushes/commits happen **only when the user asks**.

---

## 8. Next steps

1. **(User)** Run `docker compose up --build` with Docker Desktop on; confirm DB health.
2. Keep this file + CHANGELOG.md updated at the end of each milestone.
