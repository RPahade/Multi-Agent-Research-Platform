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
- [ ] Milestone 5–8 — *(awaiting details)*

> The user provides milestone requirements one at a time. Do **not** build ahead of
> the current milestone. Ask for the next milestone's details when the current is done.

### Workflow convention (per milestone)
1. **Design first** — propose the design, confirm key decisions with the user, get sign-off.
2. **Then implement** — build against the agreed design.
3. **Then document** — update WORKING.md + CHANGELOG.md at the end of the milestone.

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
| Live `/api/v1/health/db` | ✅ `200` (DB reachable) |
| Git commit + push to GitHub | ✅ M1 done; ⏳ M2 not yet committed/pushed |

**DBeaver / psql access:** connect to `localhost:5432`, db `research`, user/pass `postgres`/`postgres`.
Tables live under `research → Schemas → public → Tables` (only while containers run; `pgdata` volume persists data).

---

## 7. Git / GitHub

- **Remote:** `origin` → https://github.com/RPahade/Multi-Agent-Research-Platform (clean URL, no token stored)
- **Branch:** `main`
- **Commit author identity:** `RPahade <rohpahade2@gmail.com>`
- **Auth note:** The machine's saved HTTPS credential belongs to a *different* GitHub
  account (`rohan-itmtb`) that lacks write access. Pushing required a Personal Access
  Token for `RPahade`. A new session pushing will hit the same 403 unless the user
  provides a PAT again or fixes the stored credential in Windows Credential Manager.
- Pushes/commits happen **only when the user asks**.

---

## 8. Next steps

1. **(User)** Run `docker compose up --build` with Docker Desktop on; confirm DB health.
2. **(User)** Provide **Milestone 2** requirements.
3. Keep this file + CHANGELOG.md updated at the end of each milestone.
