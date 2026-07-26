# FRONTEND.md — Frontend Integration Guide

> **For the frontend build.** This is the self-contained
> contract for consuming the backend. The **authoritative** API spec is always the live
> **`http://localhost:8000/openapi.json`** (rendered at **`/docs`** Swagger, **`/redoc`**).
> Read this file + that spec; you do not need the backend source to build the UI.

_Backend status: all 8 backend milestones complete (see WORKING.md / CHANGELOG.md)._

---

## 1. Basics

| Thing | Value |
|-------|-------|
| Base URL (dev) | `http://localhost:8000` |
| API prefix | `/api/v1` |
| Interactive docs | `/docs` (Swagger), `/redoc` (ReDoc), `/openapi.json` |
| Auth | JWT Bearer (access + refresh) |
| CORS | allows `http://localhost:4200` by default (Angular dev). Add origins via backend `CORS_ORIGINS`. |
| Content type | JSON everywhere **except** login (form-encoded) and document upload (multipart) |
| Error shape | `{"detail": "..."}` (422 validation errors: `{"detail": [{"loc", "msg", "type"}]}`) |

**Run the backend for FE dev:** `docker compose up -d` (from repo root). Health: `GET /api/v1/health`.

**Dev proxy (recommended):** proxy `/api` → `http://localhost:8000` in the Angular dev server
(`proxy.conf.json`) so you avoid CORS entirely in development and hit same-origin `/api/v1/...`.

---

## 2. Authentication flow

1. **Login** — `POST /api/v1/auth/login`
   - **Content-Type: `application/x-www-form-urlencoded`** (OAuth2 password form), fields:
     - `username` = the user's **email**
     - `password`
   - Response: `{ "access_token", "refresh_token", "token_type": "bearer" }`
2. **Authenticated calls** — send header `Authorization: Bearer <access_token>`.
3. **Access token** lives ~30 min. On a `401`, **refresh**:
   - `POST /api/v1/auth/refresh` with JSON `{ "refresh_token": "..." }` → new `{access_token, refresh_token}`.
   - **Rotation:** the old refresh token is invalidated; always store the newest one.
4. **Logout** — `POST /api/v1/auth/logout` with JSON `{ "refresh_token": "..." }` (requires a valid access token). Revokes the refresh token server-side.
5. **Current user** — `GET /api/v1/auth/me` → `{ id, email, full_name, role, is_active, created_at }`.

**Token storage:** access token in memory (or short-lived); refresh token in a secure store.
Implement an HTTP interceptor: attach the Bearer token; on 401, try refresh once, then retry;
if refresh fails, redirect to login.

**Seeded admin (dev):** `admin@example.com` / `ChangeMe123!` (from backend `.env`).

---

## 3. Roles & RBAC (drives route guards + UI)

Roles: **`admin`**, **`analyst`**, **`leadership`**.

| Capability | admin | analyst | leadership |
|------------|:---:|:---:|:---:|
| Read agents/tools/reports/jobs/documents | ✅ | ✅ | ✅ |
| Manage **users** (CRUD) | ✅ | ❌ | ❌ |
| Create/update/delete **agents**, **tools** | ✅ | ❌ | ❌ |
| Create/update/delete **reports** | ✅ | ✅ | ❌ (read-only) |
| Create/cancel **jobs**, upload/delete **documents** | ✅ | ✅ | ❌ (read-only) |

Build route guards from `role`. A forbidden call returns **403**; not-found **404**; conflict **409**.

---

## 4. Endpoint map (shapes: see `/openapi.json` — every model has an Example)

All under `/api/v1`. Lists are **paginated + filtered** (see §5).

- **Auth:** `POST /auth/login`, `POST /auth/refresh`, `POST /auth/logout`, `GET /auth/me`
- **Users** (admin): `GET /users`, `GET /users/{id}`, `POST /users`, `PATCH /users/{id}`, `DELETE /users/{id}`
- **Agents:** `GET /agents`, `GET /agents/{id}`, `POST/PATCH/DELETE` (writes admin)
- **Tools:** `GET /tools`, `GET /tools/{id}`, `POST/PATCH/DELETE` (writes admin)
- **Reports:** `GET /reports`, `GET /reports/{id}`, `GET /reports/{id}/versions`, `POST/PATCH/DELETE` (writes analyst+admin)
- **Jobs:** `POST /jobs` (async; optional `Idempotency-Key` header), `GET /jobs`, `GET /jobs/{id}`,
  `GET /jobs/{id}/steps` (per-tool trace), `POST /jobs/{id}/cancel`, `GET /jobs/{id}/stream` (**SSE**)
- **Documents:** `POST /documents` (**multipart** `file=`), `GET /documents`, `GET /documents/{id}`,
  `GET /documents/{id}/chunks`, `DELETE /documents/{id}` (writes analyst+admin)
- **Status:** `GET /mcp/status`, `GET /events/status`

---

## 5. Pagination & filtering

List endpoints accept `?page=1&size=20` and return:
```json
{ "items": [ ... ], "total": 123, "page": 1, "size": 20, "pages": 7 }
```
Per-entity filters (query params): users `role`, `is_active`, `q`; agents `is_active`, `q`;
tools `category`, `enabled`, `q`; reports `status`, `job_id`, `q`; jobs `status`, `type`;
documents `status`, `q`.

---

## 6. The core UX flows to build

**Analyst — run research:**
1. `POST /documents` (multipart) → get `{ document, ingestion_job_id }`.
2. Poll `GET /jobs/{ingestion_job_id}` (or stream) until the document's `status` is `ingested`.
3. `POST /jobs` with `{ type:"research", input:{ query, document_ids:[...], top_k } }`.
4. **Stream** `GET /jobs/{id}/stream` (SSE) → live `status`/`progress`/`current_step`.
5. On success, `GET /reports?job_id={id}` → render `content` (title, summary, sections, citations).

**Admin:** manage users, agents, tools (CRUD tables + forms).
**Leadership:** read-only dashboards of reports/jobs.

**Job event shape** (from `GET /jobs/{id}`, the SSE stream, and Kafka):
`{ status: pending|running|succeeded|failed|cancelled, progress: 0..100, current_step, error }`.

---

## 7. Real-time (SSE) — important FE note

`GET /jobs/{id}/stream` returns `text/event-stream`; each event is `data: {json}\n\n`, closing
on a terminal status.

Auth accepts the access token from **either** the `Authorization: Bearer` header **or** a
**`?token=<access_token>` query parameter** — so the browser's native `EventSource` works
directly:
```js
const es = new EventSource(`/api/v1/jobs/${id}/stream?token=${accessToken}`);
es.onmessage = (e) => { const ev = JSON.parse(e.data); /* {status, progress, current_step, ...} */ };
```
The stream closes on a terminal status (`succeeded`/`failed`/`cancelled`). Polling
`GET /jobs/{id}` every ~1s is a fine fallback. (Note: a query-param token can appear in logs;
for production prefer a short-lived token or a fetch-based reader with a header.)

---

## 8. Suggested project layout (monorepo)

Create the app under **`frontend/`** (the repo is a monorepo: `backend/` + `frontend/`).
Add the `frontend` service to `docker-compose.yml` later if you want it containerised.

## 9. Backend changes the FE may want (raise these in the backend chat)
- ✅ Query-param token for the SSE stream endpoint — **done** (`?token=`, see §7).
- A `GET /api/v1/auth/me`-based "session bootstrap" is already there; add refresh-on-expiry client-side.
- CORS: add the deployed frontend origin to `CORS_ORIGINS` for non-dev.
- (Optional) exporters (DOCX/PDF report download) and Langfuse — not built yet.
