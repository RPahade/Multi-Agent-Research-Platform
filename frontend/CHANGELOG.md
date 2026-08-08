# CHANGELOG — Frontend

All notable frontend changes, logged per milestone.
Format is loosely based on [Keep a Changelog](https://keepachangelog.com/).
For the *current overall state*, see [FRONTEND_WORKING.md](FRONTEND_WORKING.md).
Backend history lives in the repo-root `CHANGELOG.md`.

---

## [Documents screen] — 2026-08-08

Not part of a numbered milestone — the last placeholder screen, built after M16 on the
user's suggestion. **No backend change required**; it uses only endpoints that already
existed.

### Added
- **`features/documents/documents-page`** replacing the placeholder:
  - **List** with status filter, debounced search, pagination, and per-row size, chunk
    count, page count and upload date. Documents you uploaded are marked "you"
    (`uploaded_by` is a bare UUID and non-admins cannot resolve names, so it is compared
    against the signed-in id rather than displayed raw).
  - **Chunk inspector** — the centrepiece. Expanding a document loads
    `GET /documents/{id}/chunks` and shows the exact passages retrieval searches over,
    with index, page and character count. Nothing else in the app exposed these, and
    report citations cannot be expanded to their source (backend request #4), so this is
    the only way to read the evidence a report was grounded in.
  - **Failed ingestion is finally visible** — an unsupported file uploads successfully
    (201) and only fails later during ingestion; the document's `error` is now shown.
  - **Ingestion job link** per row, reusing the M13 live progress view.
  - **Upload and delete** for analyst + admin, read-only for leadership. Delete warns
    that it is not reversible — there is no re-ingest endpoint, so recovery means
    uploading the file again.
- **`features/documents/upload-rules.ts`** — the parser's allowlist, size cap and
  validation extracted into one place, now shared with the research form's picker so the
  two can never disagree about what is accepted.

### Verified
20 automated browser checks against the live backend, all passing:
- list, paginator total, and per-row metadata all match the API
- expanding a document showed **4 real passages** of contract text; the count matched the
  API for that document, and each showed its index and character count
- status filter and search matched API-reported totals
- an unsupported `.zip` was rejected in the browser and **never sent**
- a real upload was followed through to `ingested`, appeared in the list (4 → 5), and
  deleting removed it (5 → 4)
- leadership can read and inspect passages but gets no upload control and no delete button

Production build clean, no warnings: initial 314.79 kB (91.27 kB transfer).

**Note for whoever runs the dev server:** writing a component's `.ts` before its `.html`
makes the dev server's rebuild fail (`NG2008: Could not find template file`) and it will
keep serving the last good bundle — the page silently looks stale. Check the serve log
before assuming the code is wrong.

---

## [Milestone 16 — Admin Panel] — 2026-08-08

**Goal:** Admin capabilities for monitoring and configuration — tool registry and quotas,
monitoring metrics, and role-based access for admin features.

**This is the final frontend milestone. No placeholder screens remain.**

### Decisions (confirmed with user)
- **Quotas were deliberately not built.** Verified there is no quota concept anywhere in
  the backend — no `quota`, `rate_limit`, `max_calls` or `daily_limit` in any schema,
  model, service or route, and no usage counters. A quota field the UI stores but nothing
  enforces would be a control that silently does nothing, the same trap as the tool
  `enabled` flag and `agent_id`. Recorded as request #12.
- **All remaining placeholders were filled in** — Users, Agents and Tools — so the final
  build has no dead navigation.

### Added
- **`features/admin/admin-page`** (`/admin`, `roleGuard(['admin'])`) — headline tiles
  (jobs, **error rate**, reports, users), a job breakdown by status and type, platform
  health (API, database, MCP tool server, Kafka), and recent failures showing each failed
  job's real error text with a link to its trace. A "needs attention" panel leads with
  problems: unreachable database or tool server, or an error rate at or above 20%.
  There is no metrics endpoint, so every figure is a real `total` from a `?size=1` page —
  about a dozen small parallel requests (`/stats` would collapse them; request #9).
- **`features/tools/tools-page` + `tools.service.ts`** — full tool registry CRUD: create,
  edit, enable/disable from the table, soft delete, category and enabled filters,
  debounced search, and a validated free-form JSON `config` editor. `key` is immutable
  once created. Carries a plain statement that these rows are a **catalogue** the agent
  pipeline never reads (request #2).
- **`features/agents/agents-page`** + create/update/delete on `agents.service.ts` — agent
  CRUD with name, model, description, system prompt, JSON config and active flag, plus
  the same honesty that prompt and model are stored but unused (request #3).
- **`features/users/users-page`** + list/get/update/delete on `users.service.ts` — user
  management with role, active and search filters; edit name, role, active state and an
  optional password reset. **Deleting your own account is disabled**, since a soft-delete
  of the signed-in admin would lock you out of the admin panel.

### Changed
- **`app.routes.ts`** — added `/admin` behind `roleGuard(['admin'])`.
- **`layout/shell`** — added an admin-only *Admin* link, and removed the top-level
  *Create user* entry: it is now a button on the Users page. The `/users/new` route is
  unchanged, so Milestone 10's registration screen still works.

### Verified
29 automated browser checks against the live backend, all passing:
- **RBAC:** analyst and leadership see neither *Admin* nor *Users*; analyst is redirected
  to `/forbidden` at `/admin`; analyst can **read** tools and agents but gets no *Add*
  button and no per-row actions
- **Metrics match the API exactly** — 57 jobs, 30 reports, and an error rate of
  **12.3%** independently computed as 7 failed of 57 finished; all five statuses break
  down (0/0/45/7/5); health reports API, database, tool server and events
- recent failures list real errors ("Required tool 'ingestion' failed…") with attempt counts
- **Tools:** create persisted with `config` saved as a real object (`max_results: 7`);
  invalid JSON rejected in the form; enable/disable toggled the backend; `key` immutable
  when editing; rename persisted; delete removed it from the registry
- **Agents:** create persisted with `temperature: 0.1` stored as an object
- **Users:** list renders, editing a name persisted, delete is disabled on your own
  account, and the page links to *Create user*

Production build clean, no warnings: initial 314.93 kB (92.02 kB transfer).
`npm test` passes.

### Not done (by design)
Quotas — see above and request #12.

---

## [Milestone 15 — Preview & Download] — 2026-08-03

**Goal:** Editable report preview, DOCX and PDF export, and version handling.

### Decisions (confirmed with user)
- **Export is client-side, both formats.** The API has no export endpoint (27 paths, no
  export/download/docx/pdf). Rather than block the milestone, DOCX is generated in the
  browser as **genuine OOXML** with the `docx` library and PDF uses the browser's own
  print-to-PDF behind a print stylesheet. Both produce real files, so nothing misleading
  ships. Cost: one dependency, lazily loaded.

### Added
- **Editable preview** on `/reports/:id` — an *Edit* toggle (analyst + admin only) that
  turns the preview into a form over the same layout: title, summary, status, and a
  `FormArray` of sections with add / remove / reorder. Citations remain read-only, being
  the agent's evidence trail rather than prose.
- **`report-export.service.ts`** — `downloadDocx()` builds a real .docx (title, status
  line, summary, sections, citations, provenance) and `printPdf()` calls the browser's
  print. The `docx` library is imported **lazily**, so it lands in its own ~411 kB chunk
  and the initial bundle grew ~1 kB.
- **Print stylesheet** in `styles.scss` — a `.no-print` convention plus rules that strip
  the shell, chat, controls and version history, flatten cards, and set sensible
  orphans/widows and page-break behaviour, so what prints is the report itself.
- **`ReportsService.update()`**, and *Restore this version*, which re-saves an old
  snapshot as a **new** version rather than rewriting history.

### Fixed
- **Section reordering did not update on screen.** With `track $index` on the sections
  `@for` plus `[formGroupName]="$index"`, moving a control leaves both unchanged from
  Angular's point of view, so the inputs kept rendering the previous control's values —
  the model reordered correctly but the rows appeared not to move. Now `track group`.
  Caught by verification, not by the compiler.

### Notes on the data model (verified, worth knowing)
- **`title` and `summary` live both as columns and inside `content` JSON, and drift.**
  Patching `content.summary` alone left the `summary` column untouched, so the report
  view (which reads columns) disagreed with the body it rendered. The editor writes both.
- **The save spreads existing `content`**, so `citations`, `warnings`, `compliance` and
  `generated_by` survive an edit.
- **Versioning is entirely server-side.** `PATCH /reports/{id}` snapshots a new version —
  confirmed v1 → v2 → v3, including for a status-only change. The UI just refreshes the
  list after saving.

### Verified
29 automated browser checks against the live backend, all passing:
- edit mode pre-fills; sections add, remove and **reorder** on screen and persist
- saving bumped the version and updated **both** columns and `content`; citations and
  provenance survived
- *Restore* wrote an old snapshot back as a new version with history intact
- **DOCX**: real file downloaded — `PK` magic bytes, a genuine `word/document.xml`,
  8.7 kB, containing title, status line, summary, both sections, citations, provenance
- **Print**: stylesheet strips sidebar, topbar, chat, actions and history while the
  report still renders; `page.pdf()` produced a valid 40 kB PDF
- leadership sees no *Edit* but keeps both exports, and the backend refuses its PATCH
  with **403**

Production build clean, no warnings: initial 314.52 kB (91.98 kB transfer).

### Known issue (pre-existing, unrelated)
`npm audit` reports 6 high-severity advisories, **all in Angular packages**
(`@angular/core` ≤ 20.3.26, XSS via event-handler attributes in `@angular/compiler`).
`docx` contributes none. `npm audit fix` patches within the existing `^20.3.0` range;
left alone so as not to change the lockfile mid-milestone.

---

## [Milestone 14 — Report chat wired to the live endpoint] — 2026-08-03

The backend delivered `POST /api/v1/reports/{report_id}/chat`, closing the only blocker.
**Milestone 14 is now complete.**

**The self-enabling design held:** the panel turned itself on with **no code change** —
the OpenAPI probe found the path on first load. What follows is reconciliation with the
shipped contract, not new UI.

### Changed
- **Message cap raised 1000 → 4000** to match `ChatRequest.maxLength`. The backend chose
  the limit; the frontend had been enforcing a placeholder.
- **A 404 no longer disables chat.** When the endpoint did not exist, a 404 meant
  "not deployed" and the panel switched itself off. In the shipped contract 404 means
  *unknown report*, so that logic would have wrongly reported "chat is not enabled" for a
  deleted report. The OpenAPI probe is now the single source of truth for availability.
- **Backend errors are shown verbatim.** The generic "That question could not be
  answered." was replaced with the API's own `detail`. This matters because the backend
  answers **503 when the language model is down and deliberately does not fabricate a
  fallback** — the user should see why, not a vague failure.

### Verified — against the real endpoint, not a stub
13 browser checks, all passing:
- the "not enabled" notice is gone and the input is enabled **by the probe alone**
- the input cap matches the contract (4000)
- a real question returned a grounded answer citing the report's 72-hour commitment,
  with **2 quoted citations** of genuine report text, each naming its section
- "What is the capital of France?" was flagged **not supported by this report** rather
  than answered
- each question is a separate `200` call to the live endpoint
- leadership can chat and gets answers (reads are open to all roles)

Backend behaviour confirmed by direct API probe beforehand: `grounded: true` with
citations for on-topic questions, `grounded: false` for off-topic, 422 blank message,
404 unknown report, 401 unauthenticated, 200 for leadership.

### Note
`citations[].source` returns `"REPORT"` with the section in `section`, rather than a
`[n]` marker — so chat citations do not line up with the report's own numbered citation
list. The UI renders whatever fields are present, so nothing breaks.

Production build clean, no warnings: initial 313.48 kB (91.05 kB transfer).

---

## [Milestone 14 — Report View] — 2026-08-02

**Goal:** Show report content with citations, add interactive chat linked to report data,
and ensure chat responses reference actual report content.

**Status: items 1 done, items 2–3 blocked on the backend.** There is **no chat endpoint
anywhere in the API** — all 26 paths checked for `chat`, `conversation`, `message`,
`ask`, `query`, `qa`. The chat UI is complete and self-enabling; it needs
`POST /reports/{id}/chat`, specified in `BACKEND_CHANGES_REQUIRED_FOR_FE.md` **section 0**.

### Decisions (confirmed with user)
- **Chat must feel realistic, so the backend comes first.** Rejected the client-side
  quote-matching alternative and the "spawn a research job per message" alternative in
  favour of a proper grounded endpoint. Build all the UI that does not depend on it now,
  and resume when the endpoint lands.
- **Blockers are called out separately** in the backend document, so the backend chat can
  see at a glance what actually stops frontend progress versus what is a nice-to-have.

### Added
- **`features/reports/report-detail-page`** — summary, sections, a numbered citation
  list, provenance (`generated_by` model/provider/tokens and the compliance PII scan), a
  link to the producing job, and version history from `GET /reports/{id}/versions`.
  Clicking a version swaps the page to that snapshot with a clear "historical snapshot"
  notice and a way back. `content` is free-form JSON, so every field is read defensively;
  `degraded: true` gets a prominent banner saying the content is a deterministic fallback.
- **`features/reports/reports-page`** — replaced the placeholder with a real paginated
  list: status filter, debounced search, rows linking to the detail view.
- **`features/reports/report-chat`** + **`report-chat.service.ts`** — the full chat
  panel: message thread, per-message citations, an explicit "not supported by this
  report" state for ungrounded answers, starter suggestions, loading and error handling.
  **It self-enables**: the service reads `/openapi.json` once and looks for a path
  matching `/reports/{…}/chat`, so the panel starts working the moment the backend ships
  the endpoint — no frontend change. A 404 from an actual send also flips it back.
- **`/openapi.json` added to `proxy.conf.json`** so the capability probe works in dev.

### Changed
- **`app.routes.ts`** — added `/reports/:id`.
- **`features/dashboard/reports-panel`** and **`features/jobs/job-detail-page`** — report
  titles now link to the new detail view; the job page gained a *Read the full report*
  button, replacing its "built in a later milestone" note.

### Fixed (both found by verification, both easy to reintroduce)
- **`[disabled]` on a reactive-form input does nothing.** The form directive owns the
  disabled state, so the chat input stayed usable while chat was unavailable. Now
  `form.disable()` / `form.enable()`.
- **`(ngSubmit)` never fired on the chat composer.** It is an output of the form
  directive, not a DOM event — a `<form>` with a bare `FormControl` and no `[formGroup]`
  has no directive attached, so clicking *Ask* silently did nothing. Converted to a
  `FormGroup` with `[formGroup]`, matching every other form in the app.

### Verified
26 automated browser checks against the live backend, all passing:
- reports list renders; search reaches the API as a single debounced `q` (20 → 7); a row
  opens the detail view
- a real report renders 2 sections with genuine prose (493 and 371 chars) and 4 citations
  each carrying its `[n]` marker
- provenance shows `gemini-flash-latest`, 2449 tokens and the PII scan result
- a degraded report is flagged as a fallback rather than a real analysis
- version history lists both versions; opening v1 shows the snapshot notice and *Back to
  current* clears it
- chat probes `/openapi.json`, shows the honest "not enabled" notice, and disables input
- **self-enable proven**: with the spec faked and the endpoint stubbed, the panel enabled
  itself, sent `{"message":"…","history":[]}` — the exact specified contract — rendered
  the answer with its supporting quote, and a follow-up replayed `history: user, assistant`
- leadership can read a full report

Production build clean, no warnings: initial 313.48 kB (91.05 kB transfer).

### Known limitation (backend request #4)
**Citation markers cannot be resolved to source text.** Citations carry
`{claim, source: "[1]"}`, but the retrieved passages are never persisted — the retrieval
step records only `{top_k, retrieved, top_score, documents_searched}`, and
`RetrievalTool` writes sources to a working copy of `job.input` that is never saved. The
UI shows each claim with its marker and states plainly that the marker cannot be expanded.

### Not done yet (by design)
Chat cannot answer anything until the backend endpoint exists. No report editing —
`POST/PATCH/DELETE /reports` are analyst+admin but no write UI is built.

---

## [Milestone 13 — Progress View] — 2026-08-02

**Goal:** Real-time job progress with a progress bar and per-tool status indicators,
updates via SSE (or polling), and job cancellation.

**Contract verified live before building** — `?token=` streaming works with unnamed
`data:` frames; an already-terminal job emits one event then closes; a bad token gives
401; cancel gives 403 for leadership, 200 for analyst, and **409** on an already-finished
job.

### Decisions (confirmed with user)
- **The jobs list was built too**, so progress views are reachable rather than depending
  on the dashboard feed or a fresh submit.
- **Submitting `/jobs/new` navigates straight to the live progress view**, replacing
  M12's static confirmation card — that card only existed because streaming did not yet.

### Added
- **`features/jobs/job-stream.service.ts`** — wraps native `EventSource` on
  `/jobs/{id}/stream?token=…` as an Observable that completes on a terminal status.
  Re-enters Angular's zone in the handlers so signal writes render.
  🔴 **Closes the stream explicitly on terminal status and on error.** This is required,
  not tidy-up: the backend ends the stream when a job finishes, and `EventSource` treats
  a closed stream as an error and reconnects *forever*. A regression check asserts the
  stream is opened exactly once.
- **`features/jobs/job-detail-page`** — the progress view at `/jobs/:id`: status badge,
  progress bar, current step, retry-attempt notice, timings and duration, the five
  pipeline tools as status indicators, and the produced report once finished.
  - **Polling fallback**: any stream error falls back to polling `GET /jobs/{id}` every
    1.5 s. This also solves token expiry — the token is baked into the stream URL and
    dies after ~30 min, but polling goes through the auth interceptor, which refreshes it.
    The view shows which mode is active.
  - **Steps are not streamed**, so the trace is refetched from `GET /jobs/{id}/steps`
    whenever `current_step` changes, merged over the known pipeline so tools that have
    not started yet still appear as `pending`.
  - **Cancel** with a confirm; a **409** means the job finished while the dialog was
    open, so the page refreshes and shows the real outcome rather than an error.
  - Notes on a cancelled job that progress can read 0% even after a step succeeded —
    progress writes are conditional on `status='running'`, so the cancel drops the last
    one, and the steps list is the truthful record.
- **`features/jobs/jobs-page`** — replaced the placeholder with a real paginated list:
  status and type filters, attempt counts, and each row linking to its progress view.
- **`JobsService.cancel()`**.

### Changed
- **`app.routes.ts`** — added `/jobs/:id`, placed after `jobs/new` so `new` is not
  matched as an id. Readable by every role; cancel is gated inside the page.
- **`features/jobs/new-job-page`** — on success it now navigates to `/jobs/:id`; the
  confirmation card, *Refresh status* and *Start another* were removed.
- **`features/dashboard/activity-panel`** — each entry gets an *Open* link to its
  progress view, placed outside the expand button (a link cannot live inside one).

### Verified
22 automated browser checks against the live backend, all passing:
- progress advanced live `0% → 20% → 40% → 60% → 80% → 100%` with the step name tracking
  each tool, and the live indicator visible while streaming
- **the stream opened exactly once and never reconnected** after closing
- **an already-finished job opened no stream at all**
- all five tools rendered with status, all `succeeded` after a good run, and the report
  appeared on completion
- cancel offered while running and hidden when terminal; cancelling flipped the job to
  `cancelled` in both UI and API, with steps showing
  `running, pending, pending, pending, pending` — only what actually ran
- a forced 409 on cancel refreshed the state instead of erroring
- jobs list renders, its filter reaches the API, and rows open the progress view
- submitting the form lands on `/jobs/:id`
- leadership can view progress but is not offered cancel

Production build clean, no warnings: initial 313.33 kB (90.97 kB transfer).

**Testing note:** puppeteer's `waitUntil: 'networkidle0'` never fires on the progress
page — the stream deliberately holds a connection open. Use `domcontentloaded`.

### Not done yet (by design)
The report shown on completion is title + summary only; the full renderer (sections,
citations, version history) belongs to a later milestone.

---

## [Milestone 12 — Research Job Form] — 2026-08-02

**Goal:** A form for creating research jobs — topic input and document upload, tool
configuration, input validation and error states.

### Decisions (confirmed with user)
- **Scope ends at job creation.** The form creates the job and shows a confirmation with
  the job id and current status. Live SSE progress, the step trace and cancel belong to
  the next milestone.
- **"Tool configuration" is what the backend actually honours, plus a read-only pipeline
  preview.** Established by reading the backend source: `orchestrator.py` calls
  `build_pipeline()` with **no arguments**, and the `tools` table is never consulted at
  runtime — so a tool row's `enabled` flag has no effect on a job, and MCP-vs-local is a
  server setting, not a per-job choice. A tool picker would have sent values the backend
  discards, so the pipeline is shown read-only and the configurable fields are the real
  ones. Per-job tool selection is logged as backend request #2.
- **`agent_id` is labelled as having no effect.** Nothing in `app/agent/` or
  `job_runner.py` reads it, and `system_prompt` appears nowhere in the agent package.
  The picker says so plainly rather than implying the choice changes the output. Logged
  as backend request #3.
- **The backend's test hooks are exposed** behind a collapsed *Advanced (testing)*
  panel — `fail_tool` and `tool_seconds` — so failure handling and visible progress can
  be demonstrated from the UI.

### Added
- **`features/jobs/new-job-page`** — the form, in four sections: Topic, Sources,
  Configuration and Advanced. Sends `Idempotency-Key` on `POST /jobs` (regenerated after
  each success) so a double-click cannot start two runs, and builds `input` from only the
  keys the orchestrator reads. On success it swaps to a confirmation showing the job id,
  status, progress and current step, with *Refresh status* and *Start another*.
- **`features/jobs/document-upload`** — upload plus document picker. Files upload one per
  request (the endpoint accepts a single file) with a real progress bar via
  `reportProgress`, then the component polls `GET /documents/{id}` every 1.5 s until the
  document is `ingested` or `failed` and auto-selects it. Validates type, size and
  emptiness **before** uploading, against the parser's real allowlist
  (`.pdf .docx .txt .md .csv .json`, 25 MB) — an unsupported type otherwise uploads fine
  and only fails later during ingestion. Shows the upload date so repeated uploads of the
  same filename can be told apart.
- **`features/jobs/pipeline-preview`** — the five backend tools in order, each labelled
  MCP or local (from `/mcp/status`) and required or optional, with a note that the
  sequence is fixed. `citation` is shown optional only while MCP serves it, matching
  `MCPCitationTool.required = False`.
- **`apiFieldErrors()`** in `core/services/api-error.ts` — pulls per-field messages out
  of a 422 so they can be mapped back onto the matching form controls.
- **`ApiService.upload()`** (multipart with progress events) and an optional `headers`
  argument on `ApiService.post()`.
- **`DocumentsService.upload()`** returning a friendly `{percent, result}` stream, and
  **`JobsService.create()`** taking the idempotency key.

### Changed
- **`app.routes.ts`** — added `/jobs/new` behind `roleGuard(['admin','analyst'])`, since
  both `POST /jobs` and `POST /documents` require the backend's `require_job_writer`.
- **`layout/shell`** — added a *New research* link, visible to admin and analyst only.
- **`layout/shell` (fix)** — the sidebar now stays pinned while the page scrolls
  (`position: sticky` + `align-self: flex-start` + `height: 100vh`). It was a plain flex
  child, so it stretched only to the layout's height and scrolled away with the content —
  obvious once the dashboard grew past one screen. `align-self` is what makes it work:
  flex items stretch by default, leaving sticky no room to move. The off-canvas drawer
  below 800px is unaffected.
- **`BACKEND_CHANGES_REQUIRED_FOR_FE.md`** — added requests #2 (per-job tool selection),
  #3 (`agent_id` should drive prompt/model) and #4 (reject unknown query params instead
  of ignoring them), and renumbered the rest.

### Verified
25 automated browser checks against the live backend, all passing — including a **real
end-to-end research run**:
- leadership sees no *New research* link and `/jobs/new` redirects to `/forbidden`
- pipeline preview renders all five tools with MCP/local and optional badges
- empty submit and a 9-character topic are rejected **without** calling `POST /jobs`;
  `top_k=99` is marked invalid
- an unsupported `.zip` is rejected in the browser and **never uploaded**
- a real `.txt` upload runs POST → poll → `ingested` and is auto-selected
- `POST /jobs` carried an `Idempotency-Key`, and the stored job input matched exactly
  what was entered (topic, `document_ids`, `top_k=8`)
- the job **ran to completion**: `succeeded`, all five tools succeeded, producing
  *"Vendor Comparison Report: Vendor A vs. Vendor B"* — 3 sections, 5 citations,
  `degraded=false`, i.e. a genuine LLM report rather than the fallback stub
- *Refresh status* re-reads the job; *Start another* returns to an empty form

Production build clean, no warnings: initial 312.99 kB (90.89 kB transfer).
`npm test` passes.

### Not done yet (by design)
No live SSE streaming, no per-tool live trace and no cancel — the confirmation is static
with a manual refresh. No report detail view.

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
