# CHANGELOG — Frontend

All notable frontend changes, logged per milestone.
Format is loosely based on [Keep a Changelog](https://keepachangelog.com/).
For the *current overall state*, see [FRONTEND_WORKING.md](FRONTEND_WORKING.md).
Backend history lives in the repo-root `CHANGELOG.md`.

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
