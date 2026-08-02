# CHANGELOG — Frontend

All notable frontend changes, logged per milestone.
Format is loosely based on [Keep a Changelog](https://keepachangelog.com/).
For the *current overall state*, see [FRONTEND_WORKING.md](FRONTEND_WORKING.md).
Backend history lives in the repo-root `CHANGELOG.md`.

---

## [Milestone 11 — Dashboard] — 2026-08-02

**Goal:** A dashboard showing a paginated list of reports, agent status and recent logs,
with filtering and sorting.

### Decisions (confirmed with user)
- **Sorting is client-side, over the loaded page, and labelled as such.** Verified
  against the live backend that sorting does not exist: `?sort=created_at&order=asc` and
  `?sort_by=title` return byte-identical results, because FastAPI silently drops unknown
  query params. The spec confirms `GET /reports` accepts only `status, job_id, q, page,
  size`. The services are written to pass sort params the moment the backend adds them.
- **"Recent logs" is the jobs feed.** There is no logs endpoint — an `audit_logs` table
  exists in the backend but nothing exposes it — and every unit of work runs as a job,
  so `GET /jobs` plus the per-tool trace from `GET /jobs/{id}/steps` is the real
  execution record.

### Added
- **Shared components**, built to be reused by every later list screen:
  - `shared/components/paginator` — driven by the `Page<T>` fields the API returns;
    emits page and page-size changes and shows "Showing X–Y of N".
  - `shared/components/status-badge` — one colour map covering every status value the
    API can return across jobs, job steps, documents, reports and agents.
  - `shared/components/empty-state` — placeholder when a list has no rows.
- **API services**, one per entity in its feature folder, each wrapping `ApiService`:
  `reports.service.ts` (list/get/versions), `jobs.service.ts` (list/get/steps),
  `agents.service.ts` (list/get), `documents.service.ts` (list/get/chunks). Params are
  listed explicitly per endpoint rather than spread from a query object — type-safe, and
  it documents which filters each endpoint actually honours.
- **`core/services/system.service.ts`** — `/health`, `/health/db`, `/mcp/status`,
  `/events/status`.
- **`features/dashboard/reports-panel`** — paginated reports table with a server-side
  status filter, a 300 ms debounced `q` search, page-size control, and click-to-sort
  column headers (title, status, version, created) with a visible note that sorting
  applies to the current page only. Flags reports whose content is `degraded`.
- **`features/dashboard/agents-panel`** — agents with active/inactive badges, model and
  version, plus the MCP tool server status and the tools it serves (an agent is only as
  available as its toolbox).
- **`features/dashboard/activity-panel`** — recent jobs with status, progress bar,
  current step, retry attempts and errors, filterable by type and status. Each row
  expands to that job's per-tool trace, fetched lazily and cached per job.
- **Table and neutral-badge styles** in `styles.scss` (`.table-scroll` so wide tables
  scroll themselves rather than the page, `th.sortable`, `.badge-neutral`).

### Changed
- **`features/dashboard/dashboard-page`** — replaced the M9 health-check placeholder
  with the real dashboard: stat tiles (reports, jobs with running/failed, documents,
  active agents — each read from the `total` of a `?size=1` page), a system status
  strip, and the three panels. Read-only and open to all three roles.

### Verified
21 automated browser checks against the live backend, all passing:
- stat tiles match the API exactly (20 reports, 45 jobs, 2 documents, 2 active agents)
- status strip shows API `ok`, database `reachable`, Kafka `agent.job.events`
- table renders one page of 10; paginator shows the true total; Next reaches
  "Showing 11–20 of 20"; page size 50 loads all 20 rows
- status filter reaches the API as `/reports?page=1&size=10&status=draft`, and the
  empty result matches the API's own count of 0 drafts
- typing in search issues **exactly one** debounced request
- Title sorts ascending, clicking again reverses, and the caveat note renders
- agent panel shows active/inactive agents and the 3 MCP tools
- expanding a job calls `/jobs/{id}/steps` and renders the trace
- activity type filter reaches the API
- leadership can read the whole dashboard

Server-side search confirmed separately against the API (`q=''`→20, `vendor`→17,
`residency`→3, `zzzznotfound`→0), because the in-browser assertion for it was weak —
it compared a 10-row page against a 20-row total, which paging alone satisfies.

Production build clean, no warnings: initial 312.25 kB (90.47 kB transfer).
Two demo agents seeded and kept: *Vendor Analyzer* (active) and *Compliance Reviewer*
(inactive).

### Not done yet (by design)
No report detail view, no document upload, no job creation or live SSE streaming, and no
CRUD write screens — the services added here are read-only.

---

## [Milestone 10 — Authentication UI] — 2026-07-26

**Goal:** Login and registration screens, secure JWT handling, and route guards for
role-based access.

### Decisions (confirmed with user)
- **Registration is an admin-gated "Create user" screen.** The backend has no public
  sign-up endpoint — verified against the live spec: there is no `/auth/register`, and
  `POST /users` answers 401 when anonymous because it is admin-only. Rather than add a
  backend endpoint, registration is an administrator creating the account, which also
  suits a tool whose roles are admin / analyst / leadership (nobody should be able to
  self-assign a role).
- **Root `README.md` / `WORKING.md` left stale on purpose** — they are the backend
  chat's files. The frontend docs stand on their own instead.

### Added
- **`core/services/token-storage.ts`** — access token in a memory-only signal, refresh
  token in `localStorage` (`mar.refresh_token`). Deliberately has no `HttpClient`
  dependency so the interceptor can read the token without a circular dependency.
- **`core/services/auth.service.ts`** — `login` (form-encoded via an `HttpParams` body,
  email in `username`), `loadCurrentUser`, `refresh`, `logout` (revokes server-side),
  `clearSession`, `restoreSession`; exposes `user` / `isAuthenticated` / `role` signals.
  `refresh()` is **single-flight**: simultaneous 401s share one request, because token
  rotation would invalidate parallel attempts.
- **`core/interceptors/auth-interceptor.ts`** — attaches the Bearer token; skips
  `/auth/login` and `/auth/refresh` (but not `/auth/logout`, which needs a valid access
  token); on 401 refreshes once and retries the original request; on refresh failure
  clears the session and routes to `/login?returnUrl=…`. A 403 is passed through
  untouched, since "not allowed" is not fixable by refreshing.
- **`core/guards/auth-guard.ts`** — `authGuard` (with `returnUrl`), `roleGuard(roles)`,
  and `guestGuard` keeping signed-in users off the login screen.
- **`features/auth/login-page`** — real reactive-form sign-in with per-field validation,
  a whole-form error banner and a loading state.
- **`features/users/create-user-page`** + **`users.service.ts`** — the registration
  screen: email, optional full name, password (8–72 chars, matching the backend's bcrypt
  limit) and role, posting to `POST /users`.
- **`features/forbidden/forbidden-page`** — 403 screen naming the user's current role.
- **Form styles** in `styles.scss`: `.field`, `.field-error`, `.field-hint`,
  `.form-error`, `.form-success`, plus invalid-state styling.

### Changed
- **`app.config.ts`** — registers `authInterceptor` via
  `provideHttpClient(withInterceptors(...))` and adds `provideAppInitializer` calling
  `restoreSession()`, so a reload restores the session *before* the app renders (the
  access token is memory-only, so otherwise guards would bounce the user to `/login`).
- **`app.routes.ts`** — `authGuard` on the shell's parent route; `roleGuard(['admin'])`
  on `/users` and the new `/users/new`; `guestGuard` on `/login`; added `/forbidden`.
- **`layout/shell`** — sidebar links are now filtered by role (a `computed` over the
  user signal), and the topbar shows the signed-in name, a role badge and Sign out.
- **`frontend/README.md`** — replaced the Angular CLI boilerplate with a real
  orientation page pointing at `FRONTEND_WORKING.md` and `CHANGELOG.md`.

### Verified
19 automated browser checks against the live backend, all passing (puppeteer-core run
from a scratch folder — **no test dependency was added to this project**):
- anonymous access to `/jobs` redirects to `/login?returnUrl=%2Fjobs`
- wrong password surfaces the backend's "Invalid email or password" and stays on `/login`
- admin login lands on `/dashboard`; topbar shows the user and role badge
- `localStorage` holds exactly one key — the access token is never persisted
- reload keeps the session using exactly **one** `/auth/refresh`, then `/auth/me`
- `/users/new` creates a real account through the live API
- forced 401s: two simultaneous failures cause exactly **one** `/auth/refresh`, both
  requests are retried, and the UI recovers
- when refresh itself fails, the session clears and the user is routed to `/login`
- sign out clears storage and the old refresh token is then rejected **401** server-side
- leadership sees no Users links and `/users` redirects to `/forbidden`
- `guestGuard` keeps a signed-in user off `/login`

Production build clean: initial 294.08 kB (85.32 kB transfer).
Test accounts created and kept: `analyst@example.com`, `leadership@example.com`.

### Not done yet (by design)
No CRUD tables or forms beyond user creation — the users/agents/tools management screens
are Milestone 11. `UsersPage` is still a placeholder.

---

## [Milestone 9 — Angular Project Setup] — 2026-07-26

**Goal:** Stand up the Angular project: routing, environment configuration for the API
base URL, and a folder structure for components, services and feature areas.

### Decisions (confirmed with user)
- **Styling:** hand-written SCSS with CSS custom properties — no UI library, no Tailwind.
  Keeps the code dependency-free and readable.
- **Refresh-token storage:** `localStorage` (access token stays in memory). Chosen so a
  page reload does not force a re-login during development.
- **SSE:** `FRONTEND.md` §7 now documents `?token=` query-param auth on
  `GET /jobs/{id}/stream`, so native `EventSource` will be used — the fetch-based SSE
  reader considered earlier is no longer needed.
- **"Modules":** Angular 20 is standalone-only, so the module boundary is expressed as
  feature folders + lazy-loaded routes rather than NgModules.

### Added
- **Angular 20 application** under `frontend/`, generated with
  `npx @angular/cli@20 new frontend --routing --style=scss --ssr=false --skip-git`.
- **`proxy.conf.json`** — proxies `/api` → `http://localhost:8000`, wired into the
  `serve` target so development is same-origin and CORS never applies.
- **Environments** — `src/environments/environment.ts` (dev, `apiUrl: '/api/v1'`) and
  `environment.prod.ts` (absolute URL), swapped by a `fileReplacements` entry on the
  production build configuration.
- **`core/models/`** — TypeScript interfaces mirroring `openapi.json`, one file per
  entity plus an `index.ts` barrel: `common` (`Page<T>`, health, MCP/Kafka status),
  `user` (+ `TokenPair`), `agent`, `tool`, `job` (+ `JobStep`, `JobEvent`), `document`
  (+ upload response, chunks), `report` (+ versions, `ReportContent`). Each entity also
  exports a `*Query` interface describing its list filters.
- **`core/services/api.service.ts`** — thin `HttpClient` wrapper: prefixes the API base
  URL, exposes `get`/`getPage<T>`/`post`/`patch`/`delete`, and drops `undefined`/`null`/
  empty params so unset filters never reach the URL.
- **`core/services/api-error.ts`** — `apiErrorMessage()` normalises the backend's
  `{detail: "..."}` and 422 `{detail: [{loc, msg}]}` shapes into one readable sentence,
  and reports an unreachable backend distinctly.
- **`layout/shell/`** — application frame (sidebar + topbar + `<router-outlet>`) with a
  hamburger that slides the sidebar in below 800px.
- **`shared/components/placeholder/`** — `<app-placeholder>` used by screens that later
  milestones build, so navigation is walkable end to end today.
- **`features/`** — one folder per screen area: `auth`, `dashboard`, `users`, `agents`,
  `tools`, `documents`, `jobs`, `reports`, `not-found`.
- **`features/dashboard/`** — the one real screen: calls `GET /health` and
  `GET /health/db` through `ApiService` and renders a connection card, proving the
  component → service → proxy → FastAPI chain.
- **`styles.scss`** — design tokens on `:root` (colour, spacing, radius, shadow, type)
  plus shared `.card` / `.btn` / `.badge` / `.muted` classes.

### Changed
- **`app.routes.ts`** — all routes defined; `/login` renders standalone, everything else
  renders inside `Shell`; `/` redirects to `/dashboard`; `**` → `NotFoundPage`. Every
  page uses `loadComponent` so its code downloads on first visit.
- **`app.config.ts`** — added `provideHttpClient()` and
  `withComponentInputBinding()` on the router (route params arrive as inputs later).
- **`app.ts` / `app.html`** — reduced the generated starter page to a bare
  `<router-outlet />`.
- **`app.spec.ts`** — replaced the generated "Hello, frontend" assertion, which no
  longer matched the root component.
- **`index.html`** — page title set to "Research Intelligence".
- **`angular.json`** — added `serve.options.proxyConfig` and the production
  `fileReplacements` block.

### Verified
- `npm run build` clean; initial bundle 277.92 kB (79.78 kB transfer), one lazy chunk
  per feature page.
- `npm start` serves on :4200; `/api/v1/health` and `/api/v1/health/db` return live
  backend JSON through the proxy.
- All 9 routes return 200 on a deep link (SPA fallback).
- Headless-browser render of `/dashboard` shows the shell plus a **Connected** card with
  live values (version `0.1.0`, env `development`, database `reachable`).

### Not done yet (by design)
No authentication, guards, interceptor or CRUD screens — those belong to Milestone 10
onward. Nothing was built ahead of this milestone.
