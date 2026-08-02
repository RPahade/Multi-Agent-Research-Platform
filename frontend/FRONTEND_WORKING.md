# FRONTEND_WORKING.md — Frontend State & Session Handoff

> Companion to the repo-root `WORKING.md` (backend). Read this first when picking up
> the frontend in a fresh chat. History lives in [CHANGELOG.md](CHANGELOG.md).
>
> The backend contract is `../FRONTEND.md`; the authoritative API spec is always the
> live `http://localhost:8000/openapi.json`.

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
| 11 | Admin CRUD — users, agents, tools | next |
| 12 | Documents & ingestion | planned |
| 13 | Research run + live job streaming | planned |
| 14 | Reports (content, citations, versions) | planned |
| 15 | Dashboards | planned |
| 16 | Polish / final | planned |

*(M11–M16 titles are the proposal; confirm each one before building it.)*

### Workflow convention (per milestone)
1. **Design first** — propose the approach, confirm decisions.
2. **Implement** against the agreed design.
3. **Verify** — build + run against the live backend, show results.
4. **Document** — update this file and `CHANGELOG.md`.
5. Commit only when asked (user commits at milestone completion).

---

## 4. Current state — what EXISTS right now (after Milestone 10)

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
        interceptors/
          auth-interceptor.ts  # attaches Bearer; 401 -> refresh once -> retry
        guards/
          auth-guard.ts        # authGuard, roleGuard(roles), guestGuard
      layout/shell/            # role-aware sidebar + topbar (user, role, sign out)
      shared/components/
        placeholder/           # <app-placeholder> used by the not-yet-built screens
      features/                # one folder per screen area
        auth/                  # LoginPage (real)
        users/                 # UsersPage (placeholder), CreateUserPage (real),
                               # users.service.ts
        dashboard/ agents/ tools/ documents/ jobs/ reports/
        forbidden/ not-found/
```

**Convention:** `core/` = loaded once (services, models, guards, interceptors).
`shared/` = reusable dumb UI. `features/` = screens; each milestone fills in its folder.

### Routes

`/login` renders standalone (no sidebar). Everything else renders inside `Shell` and
requires a signed-in user (`authGuard` on the parent route).

| Path | Component | Guard | State |
|---|---|---|---|
| `/login` | `LoginPage` | `guestGuard` | **real** |
| `/` | → redirects to `/dashboard` | | |
| `/dashboard` | `DashboardPage` | auth | **real** — live backend health card |
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

---

## 8. Next steps

**Milestone 11 — Admin CRUD (users, agents, tools):** a reusable paginated/filterable
table component plus a reactive-form modal pattern, then the three admin entities built
on top of it. `UsersPage` is still a placeholder and `users.service.ts` currently has
only `create()` — extend it with list/get/update/delete. Write actions must be hidden
for roles that cannot perform them (agents/tools writes are admin-only; reports writes
are analyst+admin), while all three roles keep read access.
