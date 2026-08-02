# Backend Changes Required for the Frontend

> **Purpose:** a single running list of backend work the Angular frontend needs, raised
> from the frontend chat. Backend work happens in the **backend chat** — nothing here is
> implemented by the frontend side.
>
> Every item below was **verified against the live API** (`http://localhost:8000/openapi.json`
> plus real requests), not assumed. Each says what the frontend does today without it.
>
> _Last updated: 2026-08-02, after frontend Milestone 12 (Research Job Form)._

---

## Status summary

| # | Request | Priority | Blocking? |
|---|---------|:---:|---|
| 1 | Sorting (`sort_by` + `order`) on list endpoints | **High** | Partially blocks the M11 "sorting" requirement |
| 2 | Per-job tool selection (`input.tools`) | **High** | Partially blocks the M12 "tool configuration" requirement |
| 3 | Make `agent_id` actually drive prompt/model | **High** | The field is accepted but has no effect |
| 4 | Reject unknown query params instead of ignoring them | Medium | No — but it hides bugs like #1 |
| 5 | Expose `audit_logs` via an API endpoint | Medium | No — jobs feed used instead |
| 6 | Report export (DOCX / PDF download) | Medium | Will block a "download report" feature |
| 7 | `q` search + date filters on `GET /jobs` | Low | No |
| 8 | A single dashboard summary/counts endpoint | Low | No — 6 calls used instead |
| 9 | CORS origin for a deployed frontend | Low | Only for non-dev deployment |
| 10 | Clean up leftover test rows | Low | No — cosmetic |

**Already delivered by the backend** (thank you — no action needed):
- ✅ **Query-param token on the SSE stream** (`GET /jobs/{id}/stream?token=…`), which lets
  the browser's native `EventSource` work. Documented in `FRONTEND.md` §7.

**Considered and NOT required:**
- ❌ **Public registration endpoint** (`POST /auth/register`). The frontend confirmed
  there is none and that `POST /users` is admin-only (401 when anonymous). The product
  decision was that registration is **an administrator creating the account**, which
  also prevents anyone self-assigning a role. No backend change wanted.

---

## 1. Sorting on list endpoints — **High priority**

### The problem

There is **no sorting anywhere in the API**, and — more dangerously — sort parameters
are *silently accepted and ignored*, because FastAPI drops unknown query params. A
client cannot tell the difference between "sorted" and "ignored".

Verified live:

```bash
GET /api/v1/reports?size=2                              # newest first
GET /api/v1/reports?size=2&sort=created_at&order=asc    # byte-identical result
GET /api/v1/reports?size=2&sort_by=title                # byte-identical result
```

All three return HTTP 200 with the same rows. Ordering is always `created_at DESC`.

Current query params accepted by each list endpoint:

| Endpoint | Filters | Sorting |
|---|---|:---:|
| `GET /users` | `role`, `is_active`, `q` | ❌ |
| `GET /agents` | `is_active`, `q` | ❌ |
| `GET /tools` | `category`, `enabled`, `q` | ❌ |
| `GET /reports` | `status`, `job_id`, `q` | ❌ |
| `GET /jobs` | `status`, `type` | ❌ |
| `GET /documents` | `status`, `q` | ❌ |

### Why it matters

Sorting is a per-milestone requirement ("Add filtering and sorting options"). Because it
must happen **before** pagination, it can only be done correctly in the database. Sorting
in the browser reorders the rows of the *current page* only — with 20 reports across 2
pages, clicking "Title ascending" sorts 10 rows, not 20, which quietly misleads the user.

### What the frontend does today

Client-side sorting of the loaded page, with a visible caveat under the table:
*"Sorting reorders the rows on this page only — the API has no sort parameter and always
returns newest first."* Honest, but a workaround.

### Requested

Add two optional query params to the list endpoints above:

- `sort_by` — an **allowlisted** column name per entity (reject anything else with 422;
  never interpolate it into SQL).
- `order` — `asc` | `desc`, defaulting to `desc`.

Suggested allowlists:

| Endpoint | Sortable columns |
|---|---|
| `/reports` | `created_at`, `updated_at`, `title`, `status`, `version` |
| `/jobs` | `created_at`, `finished_at`, `status`, `type`, `progress` |
| `/documents` | `created_at`, `filename`, `status`, `size_bytes`, `chunk_count` |
| `/agents` | `created_at`, `name`, `is_active` |
| `/tools` | `created_at`, `name`, `category`, `enabled` |
| `/users` | `created_at`, `email`, `role`, `is_active` |

Keep the current behaviour as the default (`created_at desc`) so nothing breaks.

**Frontend readiness:** the services are already written to pass these through — only the
parameter names need to match. Switching is a few lines once the endpoints support it.

**Also worth considering:** reject unknown query params with a 422 rather than ignoring
them. Silent acceptance is what made this bug invisible in the first place.

---

## 2. Per-job tool selection — **High priority**

### The problem

The tool pipeline is **fixed and not configurable per job**. In
`app/agent/orchestrator.py`:

```python
pipeline = build_pipeline()          # takes no arguments
```

and `app/agent/tools/__init__.py` returns a hard-coded list:
`retrieval → research → synthesis → citation → compliance`.

Consequences:

- **The `tools` table is never consulted at runtime.** A tool row's `enabled` flag has
  no effect on any job — the pipeline instantiates tool classes directly.
- **MCP-vs-local is a server setting**, not a per-job choice (`settings.mcp_enabled`).
- Nothing in `job.input` can add, remove or reorder a step.

### Why it matters

A frontend milestone asked for "allow tool configuration". The only honest thing the UI
can offer today is a **read-only** pipeline preview, because any tool picker would be
sending values the backend discards.

### What the frontend does today

`/jobs/new` shows the five steps read-only, each labelled MCP or local and required or
optional, with a note saying the sequence is fixed by the backend. It configures only
what the backend genuinely honours: `input.query`, `input.document_ids`, `input.top_k`,
`max_attempts`, and the `fail_tool` / `tool_seconds` test hooks.

### Requested

Let a job choose its pipeline, e.g. `input.tools: ["retrieval","synthesis","compliance"]`
passed through to `build_pipeline(selected)`. Validate against the known tool keys
(422 on anything unknown), and keep the full pipeline as the default when omitted.
Honouring the `tools` table's `enabled` flag would be a reasonable alternative.

---

## 3. Make `agent_id` actually affect execution — **High priority**

### The problem

`POST /jobs` accepts `agent_id`, stores it on the job, and **nothing ever reads it
during execution**. Verified: no reference to `agent_id` anywhere in `app/agent/` or
`app/services/job_runner.py`, and `system_prompt` appears nowhere in the agent package.

The `agents` table carries `system_prompt`, `model` and `config` (temperature, etc.),
but `SynthesisTool` uses the globally configured provider and model instead.

### Why it matters

Configurable agents are a headline feature — the Agents CRUD screens exist to edit a
prompt and model that currently change nothing. Selecting "Vendor Analyzer" versus
"Compliance Reviewer" produces identical output.

### What the frontend does today

The agent picker on `/jobs/new` is labelled honestly: *"Recorded on the job for
provenance. The backend does not yet use it to change the prompt or model, so picking
one will not alter the result."* That label should be deleted once this is fixed.

### Requested

When a job has an `agent_id`, load the agent and use its `system_prompt`, `model` and
`config` for the synthesis step, falling back to the current global defaults when no
agent is set.

---

## 4. Reject unknown query params — Medium

Related to #1, and the reason it went unnoticed. FastAPI ignores query params it does
not declare, so `?sort_by=title` returns 200 with unsorted data — indistinguishable from
success. A client cannot detect the difference.

**Requested:** reject unrecognised query params with 422 (e.g. a strict dependency or a
`model_config = ConfigDict(extra="forbid")` on the query models). Failing loudly turns a
silent no-op into an obvious error.

---

## 5. Expose `audit_logs` through an API — Medium

`WORKING.md` documents an `audit_logs` table (added in backend M2, BIGINT PK,
high-volume), but **no endpoint exposes it** — confirmed: no path matching `audit` in
the spec's 26 paths.

**Why it matters:** the product promises "auditable logs for compliance". A compliance
reviewer wants *who changed what, when* — which the jobs feed cannot answer, because it
records agent execution, not user actions.

**What the frontend does today:** the dashboard's "Recent activity" is built from
`GET /jobs` plus `GET /jobs/{id}/steps` (the per-tool trace). That is the real execution
record and works well, but it is not an audit trail.

**Requested:** `GET /api/v1/audit-logs`, paginated and filtered like every other list
endpoint (`user_id`, `action`, `entity_type`, `entity_id`, date range), admin-only.

---

## 6. Report export — DOCX / PDF download — Medium

Noted as not built in `FRONTEND.md` §9; confirmed no `export` or `download` path exists.
`JobType` already includes an `export` member, so the groundwork is partly there.

**Why it matters:** a cited research report that cannot leave the browser has limited
value to a procurement team. This will block a "Download report" button when the report
detail screen is built.

**Requested:** `GET /api/v1/reports/{id}/export?format=docx|pdf` returning the file with
an appropriate `Content-Disposition`. If generation is slow, returning an `export` job id
and reusing the existing job/SSE machinery would fit the current architecture well.

---

## 7. `q` search and date filters on `GET /jobs` — Low

`GET /jobs` accepts only `status` and `type` — no free-text search, unlike `/reports`,
`/documents`, `/users`, `/agents` and `/tools`, which all have `q`.

**Requested:** add `q` (matching the job's `input.query` text) and optionally
`created_after` / `created_before`. Useful once the jobs screen holds hundreds of rows.

---

## 8. A dashboard summary endpoint — Low

The dashboard needs six counts. With no counts endpoint, the frontend issues **six
parallel `?size=1` requests** and reads each `total`:

```
/reports?size=1  /jobs?size=1  /jobs?size=1&status=running
/jobs?size=1&status=failed  /documents?size=1  /agents?size=1&is_active=true
```

It works and is fast enough locally, but it is six round-trips and six DB counts for one
screen.

**Requested (nice-to-have):** `GET /api/v1/stats` returning the counts in one response —
e.g. totals for reports/jobs/documents/agents plus a job breakdown by status.

---

## 9. CORS for a deployed frontend — Low

Already noted in `FRONTEND.md` §9. `CORS_ORIGINS` currently allows `http://localhost:4200`.
Any non-dev deployment needs its origin added. **No action needed while developing** —
the Angular dev server proxies `/api` to `:8000`, so requests are same-origin.

---

## 10. Leftover test rows — Low (data, not code)

Not a code change, but visible in the UI:

- **`GET /tools` returns a single junk row** — `key: tool_9887e4`, name `T`, no
  description. It is the only tool in the database, so the Tools screen will show one
  meaningless entry. Meanwhile the MCP server serves three real tools
  (`web_research`, `verify_citations`, `redact_pii`) that have no rows in `tools`.
- **A leftover agent** named `Vendor Analyzer` with no model and the description `d`.

**Suggested:** seed the three real MCP tools as proper `tools` rows so the Tools screen
reflects the actual toolbox. Per the standing rule, the frontend does **not** delete rows.

---

## How to use this file

When a request here is delivered, move it to the "Already delivered" list at the top with
a ✅ and update `FRONTEND.md` if the contract changed. The frontend chat appends new
requests as later milestones surface them.
