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
| 10 | Authentication, app shell, RBAC routing | next |
| 11 | Admin CRUD — users, agents, tools | planned |
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

## 4. Current state — what EXISTS right now (after Milestone 9)

### Folder structure

```
frontend/
  proxy.conf.json              # /api -> http://localhost:8000 (dev only)
  angular.json                 # proxyConfig + prod fileReplacements wired in
  src/
    environments/
      environment.ts           # dev   — apiUrl '/api/v1'  (through the proxy)
      environment.prod.ts      # prod  — apiUrl 'http://localhost:8000/api/v1'
    styles.scss                # design tokens (:root vars) + .card/.btn/.badge
    app/
      app.ts / app.html        # root — hosts <router-outlet> only
      app.config.ts            # provideRouter + provideHttpClient
      app.routes.ts            # all routes, every page lazy-loaded
      core/                    # app-wide singletons
        models/                # TS interfaces mirroring openapi.json + index.ts barrel
        services/
          api.service.ts       # HttpClient wrapper (base URL + param cleaning)
          api-error.ts         # apiErrorMessage() — normalises {detail} and 422 arrays
      layout/shell/            # sidebar + topbar + <router-outlet>
      shared/components/
        placeholder/           # <app-placeholder> used by the not-yet-built screens
      features/                # one folder per screen area
        auth/ dashboard/ users/ agents/ tools/
        documents/ jobs/ reports/ not-found/
```

**Convention:** `core/` = loaded once (services, models, later guards/interceptors).
`shared/` = reusable dumb UI. `features/` = screens; each milestone fills in its folder.

### Routes

`/login` renders standalone (no sidebar). Everything else renders inside `Shell`.

| Path | Component | State |
|---|---|---|
| `/login` | `LoginPage` | placeholder |
| `/` | → redirects to `/dashboard` | |
| `/dashboard` | `DashboardPage` | **real** — live backend health card |
| `/documents` `/jobs` `/reports` `/users` `/agents` `/tools` | feature pages | placeholder |
| `**` | `NotFoundPage` | real |

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

Milestone 9, verified against the live backend on 2026-07-26:

- `npm run build` — clean, no warnings. Initial bundle 277.92 kB (79.78 kB transfer);
  each feature emits its own lazy chunk.
- `npm start` — dev server up on :4200.
- `GET /api/v1/health` **through the proxy** → `{"status":"ok", ...}`.
- `GET /api/v1/health/db` through the proxy → `{"status":"ok","database":"reachable"}`.
- All 9 routes return 200 on a deep link (SPA fallback works).
- Headless-browser render of `/dashboard` shows the sidebar, the topbar and a
  **Connected** card populated with live values (app name, version `0.1.0`,
  env `development`, database `reachable`).

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

---

## 8. Next steps

**Milestone 10 — Authentication, app shell, RBAC routing:**
login form (form-encoded, `username` = email), `AuthService` on signals, token storage
(access in memory, refresh in `localStorage`), an HTTP interceptor that attaches the
Bearer token and on a 401 refreshes once then retries, `/auth/me` session bootstrap on
reload, logout that revokes the refresh token, `authGuard` + `roleGuard`, and a
role-aware sidebar that hides what the signed-in role cannot use.
