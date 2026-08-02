# Frontend — Multi-Agent Research Intelligence Platform

Angular 20 UI for the research platform. Analysts upload source documents, ask a
research question, watch the agent job run, and read the cited report it produces.

> **Working on this code? Start with [FRONTEND_WORKING.md](FRONTEND_WORKING.md)** —
> current state, folder map, conventions, decisions and next steps.
> History per milestone is in [CHANGELOG.md](CHANGELOG.md).
> The backend API contract is [`../FRONTEND.md`](../FRONTEND.md); the authoritative
> spec is always the live `http://localhost:8000/openapi.json`.

## Run it

The backend must be running first — the UI is useless without it.

```bash
# 1. backend, from the repo root
docker compose up -d          # health check: http://localhost:8000/api/v1/health

# 2. frontend, from this folder
npm install                   # first time only
npm start                     # http://localhost:4200
```

Sign in with the seeded admin: `admin@example.com` / `ChangeMe123!`

The dev server proxies `/api` to `http://localhost:8000` (see `proxy.conf.json`), so
the app calls same-origin `/api/v1/...` and CORS never applies in development.

## Commands

| Command | What it does |
|---|---|
| `npm start` | Dev server on :4200 with the API proxy |
| `npm run build` | Production build into `dist/frontend` |
| `npm test` | Unit tests (Karma + Jasmine) |

## How it is organised

```
src/app/
  core/        loaded once — API models, services, guards, interceptors
  shared/      reusable presentational components
  layout/      the app shell (sidebar + topbar)
  features/    one folder per screen area
```

Full details, conventions and the route table are in
[FRONTEND_WORKING.md](FRONTEND_WORKING.md).
