# FRONTEND_WORKING.md — Frontend State & Session Handoff

> Companion to the repo-root `WORKING.md` (backend). Read this first when picking up
> the frontend in a fresh chat. History lives in [CHANGELOG.md](CHANGELOG.md).
>
> The backend contract is `../FRONTEND.md`; the authoritative API spec is always the
> live `http://localhost:8000/openapi.json`.
>
> Backend work the frontend needs is tracked in
> [`../BACKEND_CHANGES_REQUIRED_FOR_FE.md`](../BACKEND_CHANGES_REQUIRED_FOR_FE.md) —
> append to it rather than burying requests in this file.

---

## 1. What this is

The Angular UI for the **Multi-Agent Research Intelligence Platform**. An analyst
uploads source documents, asks a research question, and an agent pipeline runs it as a
background job and produces a cited report. Three roles — `admin` (governance),
`analyst` (day-to-day work), `leadership` (read-only).

---

## 2. Tech stack (confirmed decisions)

| Decision | Choice | Why |
|---|---|---|
| Framework | Angular 20, standalone components (no NgModules) | Current stable; standalone is the default |
| State | Signals | Built in, simpler than a store for this app's size |
| Forms | Reactive Forms | Typed, validates cleanly |
| HTTP | `HttpClient` + a functional auth interceptor | Interceptor arrives with authentication |
| Styling | **Hand-written SCSS + CSS custom properties** | No dependency, every line readable |
| Refresh-token storage | **`localStorage`** | Survives reload; access token stays in memory |
| Live job progress | **Native `EventSource` with `?token=`** | Backend accepts a query-param token (`FRONTEND.md` §7) |
| Dev API access | Dev-server proxy `/api` → `:8000` | Same-origin in dev, so no CORS |

---

## 3. Milestone roadmap (Frontend = 8 milestones, M9–M16)

| # | Milestone | Status |
|---|---|---|
| 9 | Angular project setup | ✅ done |
| 10 | Authentication UI — login, registration, JWT handling, route guards | ✅ done |
| 11 | Dashboard — paginated reports, agent status, recent logs, filter/sort | ✅ done |
| 12 | Research Job Form — topic, upload, configuration, validation | ✅ done |
| 13 | *to be confirmed* | next |
| 14–16 | *to be confirmed* | planned |

*(The user supplies each milestone's definition; do not assume the remaining titles.
Still unbuilt and expected somewhere in M13–M16: live SSE job progress with the
step-by-step trace and cancel, report detail with citations and versions, a documents
management screen, and the users/agents/tools CRUD write screens.)*

### Workflow convention (per milestone)
1. **Design first** — propose the approach, confirm decisions.
2. **Implement** against the agreed design.
3. **Verify** — build + run against the live backend, show results.
4. **Document** — update this file and `CHANGELOG.md`.
5. Commit only when asked (user commits at milestone completion).

---

## 4. Current state — what EXISTS right now (after Milestone 12)

### Folder structure

```
frontend/
  proxy.conf.json              # /api -> http://localhost:8000 (dev only)
  angular.json                 # proxyConfig + prod fileReplacements wired in
  src/
    environments/
      environment.ts           # dev   — apiUrl '/api/v1'  (through the proxy)
      environment.prod.ts      # prod  — apiUrl 'http://localhost:8000/api/v1'
    styles.scss                # design tokens (:root vars) + .card/.btn/.badge/.field
    app/
      app.ts / app.html        # root — hosts <router-outlet> only
      app.config.ts            # router + http + interceptor + session bootstrap
      app.routes.ts            # all routes, every page lazy-loaded, guards applied
      core/                    # app-wide singletons
        models/                # TS interfaces mirroring openapi.json + index.ts barrel
        services/
          api.service.ts       # HttpClient wrapper (base URL + param cleaning)
          api-error.ts         # apiErrorMessage() — normalises {detail} and 422 arrays
          token-storage.ts     # access token in memory, refresh token in localStorage
          auth.service.ts      # login/logout/refresh/me + user, role, isAuthenticated
          system.service.ts    # /health, /health/db, /mcp/status, /events/status
        interceptors/
          auth-interceptor.ts  # attaches Bearer; 401 -> refresh once -> retry
        guards/
          auth-guard.ts        # authGuard, roleGuard(roles), guestGuard
      layout/shell/            # role-aware sidebar + topbar (user, role, sign out)
      shared/components/
        placeholder/           # <app-placeholder> used by the not-yet-built screens
        paginator/             # pager driven by Page<T>; emits page/size changes
        status-badge/          # colours every status value the API returns
        empty-state/           # "nothing to show" message
      features/                # one folder per screen area
        auth/                  # LoginPage (real)
        dashboard/             # DashboardPage + reports-panel, agents-panel,
                               # activity-panel (all real)
        users/                 # UsersPage (placeholder), CreateUserPage (real),
                               # users.service.ts
        jobs/                  # NewJobPage + document-upload, pipeline-preview,
                               # jobs.service.ts (JobsPage itself is a placeholder)
        reports/ agents/ documents/          # placeholder pages + their API services
        tools/ forbidden/ not-found/
```

**Where API calls live:** one service per entity in its feature folder
(`reports.service.ts`, `jobs.service.ts`, `agents.service.ts`,
`documents.service.ts`, `users.service.ts`), each wrapping `ApiService`. Cross-cutting
status endpoints live in `core/services/system.service.ts`.

**Note on query params:** each service lists the endpoint's supported params
explicitly rather than spreading a query object. That keeps the call type-safe (a
TypeScript interface is not assignable to `Record<string, …>`) and documents exactly
which filters the endpoint honours.

**Convention:** `core/` = loaded once (services, models, guards, interceptors).
`shared/` = reusable dumb UI. `features/` = screens; each milestone fills in its folder.

### Routes

`/login` renders standalone (no sidebar). Everything else renders inside `Shell` and
requires a signed-in user (`authGuard` on the parent route).

| Path | Component | Guard | State |
|---|---|---|---|
| `/login` | `LoginPage` | `guestGuard` | **real** |
| `/` | → redirects to `/dashboard` | | |
| `/dashboard` | `DashboardPage` | auth | **real** — full dashboard (M11) |
| `/jobs/new` | `NewJobPage` | auth + `roleGuard(['admin','analyst'])` | **real** — research form (M12) |
| `/users/new` | `CreateUserPage` | auth + `roleGuard(['admin'])` | **real** — registration |
| `/users` | `UsersPage` | auth + `roleGuard(['admin'])` | placeholder |
| `/documents` `/jobs` `/reports` `/agents` `/tools` | feature pages | auth | placeholder |
| `/forbidden` | `ForbiddenPage` | auth | real |
| `**` | `NotFoundPage` | — | real |

**Why so little role gating:** per FRONTEND.md §3 all three roles may *read* every
section, so only user management is restricted at the route level. Write permissions
(hiding Create/Edit/Delete from leadership) belong to each CRUD milestone.

### Authentication (Milestone 10)

- **Token handling** — access token in memory (`TokenStorage`, never persisted);
  refresh token in `localStorage` under `mar.refresh_token`. The backend **rotates**
  refresh tokens, so every new pair immediately replaces the old one.
- **Login** is form-encoded (`HttpParams` body ⇒ Angular sets the OAuth2
  `application/x-www-form-urlencoded` content type), with the email in `username`.
- **Session bootstrap** — `provideAppInitializer` calls `AuthService.restoreSession()`
  before the app renders: with only a refresh token surviving a reload, it exchanges it
  for a new access token then loads `/auth/me`. Without this the guards would bounce a
  signed-in user to `/login` on every refresh.
- **Interceptor** attaches the Bearer token, skips `/auth/login` and `/auth/refresh`
  (but *not* `/auth/logout`, which needs a valid access token), and on a 401 refreshes
  once and retries. A 403 is passed through untouched — that means "signed in but not
  allowed", which is not fixable by refreshing.
- **Single-flight refresh** — `AuthService.refresh()` caches the in-progress request so
  simultaneous 401s share one call. Firing several in parallel would fail, because
  rotation invalidates each token as the next call consumes it.
- **Registration** is an admin-gated *Create user* screen (`/users/new` → `POST /users`).
  The backend has no public sign-up endpoint — confirmed against the live spec — so
  self-service registration is not possible without a backend change.

### Dashboard (Milestone 11)

`/dashboard` is composed of four parts, read-only and open to all three roles (everyone
can read reports, jobs and agents, so no role gating applies):

1. **Stat tiles** — reports, jobs (with running/failed counts), documents, active
   agents. Each count is the `total` of a `?size=1` page, the cheapest way to ask
   "how many?" with the endpoints available.
2. **Status strip** — API, database and Kafka event pipeline.
3. **Reports panel** — paginated table with a server-side status filter and a debounced
   `q` search (300 ms), plus client-side column sorting.
4. **Agent status** (agents + the MCP tool server) and **Recent activity** (the jobs
   feed, each row expandable to its per-tool trace, loaded lazily and cached per job).

⚠️ **Two API limitations shape this screen — verified against the live backend:**

- **There is no sorting.** `?sort=`, `?order=` and `?sort_by=` are silently ignored
  (FastAPI drops unknown query params), so results are byte-identical with or without
  them. Ordering is always `created_at DESC`. Column sorting is therefore **client-side
  over the loaded page only**, and the UI says so beneath the table. `ReportsService`
  is ready to pass sort params the moment the backend supports them — raise that in the
  backend chat if server-side sorting is wanted.
- **There is no logs endpoint.** An `audit_logs` table exists in the backend but nothing
  exposes it. The jobs feed is the real execution record, so "recent logs" is built from
  `GET /jobs` plus `GET /jobs/{id}/steps`.

### Research job form (Milestone 12)

`/jobs/new`, guarded with `roleGuard(['admin','analyst'])` — both `POST /jobs` and
`POST /documents` require the backend's `require_job_writer`, so leadership must never
reach it.

**What the form sends.** Only keys the orchestrator actually reads:

| Field | Sent as | Notes |
|---|---|---|
| Topic | `input.query` | required, 10–2000 chars, trimmed |
| Documents | `input.document_ids` | omitted when nothing is selected = search everything |
| Retrieval depth | `input.top_k` | 1–20, backend default 5 |
| Retry budget | `max_attempts` | 1–10, default 3 |
| Agent | `agent_id` | **stored only, no execution effect** — see below |
| Advanced | `input.fail_tool`, `input.tool_seconds` | backend test hooks |

**Upload flow.** The endpoint takes **one file per request**, so files upload
sequentially with a real progress bar (`reportProgress` on the multipart POST). The
response gives `{document, ingestion_job_id}`; the component then polls
`GET /documents/{id}` every 1.5 s (capped at ~90 s) until `ingested` or `failed`, and
auto-selects the document once ingested. Watching the *document* rather than the job
gives the failure reason directly.

**Client-side file validation matters here.** The parser's real allowlist is
`.pdf .docx .txt .md .csv .json`; anything else uploads successfully (201) and only
fails later during ingestion. Checking in the browser turns a delayed, confusing failure
into an immediate message — and saves the wasted upload.

**Idempotency.** `POST /jobs` carries a generated `Idempotency-Key`, regenerated after
each success, so a double-click returns the existing job instead of starting a second run.

⚠️ **Two more API limitations, verified by reading the backend source:**

- **The tool pipeline is fixed.** `orchestrator.py` calls `build_pipeline()` with no
  arguments, and the `tools` table is never consulted at runtime — a tool row's
  `enabled` flag has no effect on a job. MCP-vs-local is a server setting. So
  "tool configuration" is a **read-only pipeline preview** plus the knobs that do work
  (`top_k`, `max_attempts`, document scoping).
- **`agent_id` has no execution effect.** Nothing in `app/agent/` or `job_runner.py`
  loads the Agent row; `system_prompt` appears nowhere in the agent package. The picker
  is labelled accordingly — **delete that label once the backend honours it.**

Both are logged in `../BACKEND_CHANGES_REQUIRED_FOR_FE.md` (items 2 and 3).

### Models (`core/models/`)

Hand-written from `openapi.json`, one file per entity plus a barrel:
`common` (`Page<T>`, health, `McpStatus`, `EventsStatus`), `user` (+ `TokenPair`),
`agent`, `tool`, `job` (+ `JobStep`, `JobEvent`), `document`, `report`.
Each entity also exports a `*Query` interface for its list filters.

### Conventions established (follow these)

- **Naming:** files are kebab-case (`users-page.ts`), classes PascalCase (`UsersPage`),
  and the file name matches the component — no `.component.ts` suffix (Angular 20 style).
- **Templates:** separate `.html`/`.scss` files once a component has real content;
  inline `template:` is fine for a handful of lines.
- **Control flow:** the built-in `@if` / `@for` / `@switch` blocks, not `*ngIf` / `*ngFor`.
- **Injection:** `inject()` in field initialisers, not constructor parameters.
- **Styling:** never hard-code a colour or spacing value — use a `var(--token)` from
  `styles.scss`. Add a new token there if one is missing.
- **HTTP:** always go through `ApiService`; never inject `HttpClient` into a component.
- **Errors:** render user-facing errors via `apiErrorMessage(err)`.
- **Lazy loading:** every route uses `loadComponent`.

---

## 5. How to run

```bash
# 1. backend (from the repo root)
docker compose up -d          # health: http://localhost:8000/api/v1/health

# 2. frontend
cd frontend
npm install                   # first time only
npm start                     # http://localhost:4200
npm run build                 # production build -> dist/frontend
```

The dev server proxies `/api` to `:8000`, so the app calls same-origin `/api/v1/...`
and CORS never applies in development.

**Seeded admin (dev):** `admin@example.com` / `ChangeMe123!`

---

## 6. Verification status

**Milestone 9** — verified against the live backend on 2026-07-26:

- `npm run build` clean; each feature emits its own lazy chunk.
- `GET /api/v1/health` and `/health/db` **through the proxy** return live JSON.
- All routes return 200 on a deep link (SPA fallback works).
- Headless render of `/dashboard` shows a **Connected** card with live values.

**Milestone 10** — 19 automated browser checks against the live backend, all passing
(driven with puppeteer-core from a scratch folder; no test dependency was added to
this project):

- `authGuard` sends an anonymous user to `/login?returnUrl=%2Fjobs`.
- A wrong password shows the backend's message ("Invalid email or password") and stays put.
- Admin login lands on `/dashboard`; the topbar shows the name and a role badge.
- `localStorage` holds exactly one key (`mar.refresh_token`) — the access token is
  never persisted.
- A full page reload keeps the session: exactly **one** `/auth/refresh` then `/auth/me`.
- `/users/new` creates a real account through the live API.
- **Interceptor, forced 401s:** two simultaneous 401s trigger exactly **one**
  `/auth/refresh`, the failed requests are retried, and the UI recovers to *Connected*.
  Observed order: `GET /health | GET /health/db | POST /auth/refresh | GET /health | GET /health/db`.
- When the refresh itself fails, the session is cleared and the user lands on
  `/login?returnUrl=…`.
- Sign out clears storage, returns to `/login`, and the old refresh token is then
  **rejected with 401** by the backend (revocation confirmed server-side).
- Leadership: sidebar hides *Users* / *Create user*, and typing `/users` directly
  lands on `/forbidden`.
- `guestGuard` redirects an already signed-in user away from `/login`.

Test accounts created for role testing (left in place per the "keep test data" rule):
`analyst@example.com` and `leadership@example.com`, both `ChangeMe123!`.

**Milestone 11** — 21 automated browser checks against the live backend, all passing:

- Stat tiles match the API exactly (20 reports, 45 jobs, 2 documents, 2 active agents).
- Status strip shows API `ok` v0.1.0, database `reachable`, Kafka `agent.job.events`.
- Reports table renders one page (10 rows) and the paginator reports the true total.
- The status filter goes to the API as a query param
  (`/reports?page=1&size=10&status=draft`) and the empty result matches the API's count.
- Typing in the search box issues **exactly one** debounced request (`q=vendor`).
- Next moves to page 2 ("Showing 11–20 of 20"); changing page size to 50 reloads and
  shows all 20 rows.
- Clicking *Title* sorts ascending, clicking again reverses, and the caveat note is
  rendered.
- Agent panel shows active/inactive agents and the three MCP tools (`web_research`,
  `verify_citations`, `redact_pii`).
- Activity feed lists jobs; expanding one calls `/jobs/{id}/steps` and renders the trace.
- The activity type filter reaches the API (`/jobs?page=1&size=8&type=ingestion`).
- Leadership can read the whole dashboard.

Server-side search confirmed separately by API: `q=''`→20, `vendor`→17, `residency`→3,
`zzzznotfound`→0. (The in-browser "search narrows results" assertion was weak — it
compared a 10-row page against a 20-row total, which paging alone satisfies. The API
check above is the real evidence.)

Two demo agents were seeded so the panel is not a single row: *Vendor Analyzer*
(active, `gemini-flash-latest`) and *Compliance Reviewer* (inactive). A pre-existing
backend test agent (also called "Vendor Analyzer", no model, description `d`) is still
there, so the list shows two similarly named entries.

**Milestone 12** — 25 automated browser checks against the live backend, all passing,
including a **real end-to-end research run**:

- Leadership sees no *New research* link and `/jobs/new` sends them to `/forbidden`;
  analyst gets the form.
- Pipeline preview renders all five backend tools with MCP/local and optional badges.
- Validation: empty submit and a 9-character topic are both rejected **without** calling
  `POST /jobs`; `top_k=99` is marked invalid.
- An unsupported file type (`.zip`) is rejected in the browser and **never uploaded**.
- A real `.txt` upload runs POST → poll → `ingested` and is auto-selected.
- Submit created the job with an `Idempotency-Key` header, and the backend job carried
  the exact topic, `document_ids` and `top_k=8` that were entered.
- **The job ran to completion**: `status=succeeded`, all five tools succeeded
  (`retrieval research synthesis citation compliance`), and it produced a real report —
  *"Vendor Comparison Report: Vendor A vs. Vendor B"*, 3 sections, 5 citations,
  `degraded=false` (a genuine LLM report, not the fallback stub).
- *Refresh status* re-reads the job; *Start another* returns to an empty form.

---

## 7. Notes, gotchas & things to know

- **Backend API observations (not FE bugs):** `GET /tools` currently holds a single
  leftover test row (`key: tool_9887e4`, name `T`), and job history is backend test data.
- **SSE:** `FRONTEND.md` §7 was updated — `GET /jobs/{id}/stream` now accepts
  `?token=<access_token>`, so plain `EventSource` works and no fetch-based SSE reader
  is needed. Polling `GET /jobs/{id}` every ~1s remains the fallback.
- **Report `content` is free-form JSON.** The usual shape is
  `{title, summary, sections[], citations[]}`, but it can also carry `degraded: true`
  (the LLM was unavailable and a stub was written), `warnings[]` and `generated_by`.
  Render defensively and surface the degraded state rather than passing a stub off as a
  real report.
- **Jobs retry.** A job can go `running → failed → running` with `attempts` incrementing
  up to `max_attempts`, so job UI must show attempts, not just a progress bar.
- **Uploads are jobs.** `POST /documents` returns `{document, ingestion_job_id}`; the
  same job-watching code drives the upload UI until `document.status` is `ingested`.
- **Idempotency.** `POST /jobs` accepts an `Idempotency-Key` header; send a generated
  UUID so a double-click cannot start two runs.
- **`ng` is not installed globally** — use `npx @angular/cli@20 …` or the npm scripts.
- **No public registration endpoint exists.** `POST /users` is admin-only (401 when
  anonymous) and there is no `/auth/register`. If self-service sign-up is ever wanted,
  it needs a backend change — raise it in the backend chat.
- **Guards are convenience, not security.** The backend enforces RBAC itself and answers
  403 regardless of what the UI shows. Never treat a hidden button as protection.
- **Known limitation — no cross-tab session sync.** `TokenStorage` reads `localStorage`
  once at construction into a signal. Signing out in one tab does not sign the other
  out until it reloads. A `storage` event listener would fix it if this ever matters.
- **Root `README.md` / `WORKING.md` are stale** (they still say "Milestone 1" and
  "`frontend/` later"). Left deliberately untouched — they are the backend chat's files.
  The frontend docs are self-sufficient; do not trust the root ones for frontend state.

- **The API has no sorting and no logs endpoint** — see the Dashboard section above.
  Don't send `sort_by`/`order` expecting them to work; they are silently ignored.

---

## 8. Next steps

**Milestone 13 is not yet defined** — the user supplies each milestone. These are the
pieces still missing, with the groundwork already in place:

- **Live job progress** — the natural follow-on from M12. `jobs.service.ts` has
  list/get/steps and `create()`; still to build: consuming `GET /jobs/{id}/stream` with
  native `EventSource` and `?token=<access_token>`, the live step trace, and
  `POST /jobs/{id}/cancel`. `/jobs/new` currently ends at a static confirmation with a
  *Refresh status* button, which is where streaming plugs in.
- **Report detail** — `reports.service.ts` has get/versions; the content renderer
  (sections, citations, degraded banner) and version history are not built.
- **Documents screen** — `documents.service.ts` has list/get/chunks/upload; a management
  screen (list, chunk inspector, delete) is not built.
- **CRUD write screens** for users/agents/tools — the services are read-only apart from
  `users.create()`. Writes must be hidden from roles that cannot perform them
  (agents/tools writes are admin-only; reports writes are analyst+admin) while all roles
  keep read access.

Reuse `Paginator`, `StatusBadge` and `EmptyState` rather than rebuilding list plumbing.
