# Backend Changes Required for the Frontend

> **Purpose:** a single running list of backend work the Angular frontend needs, raised
> from the frontend chat. Backend work happens in the **backend chat** — nothing here is
> implemented by the frontend side.
>
> Every item below was **verified against the live API** (`http://localhost:8000/openapi.json`
> plus real requests), not assumed. Each says what the frontend does today without it.
>
> _Last updated: 2026-08-02, after frontend Milestone 14 (Report View)._

---

# 🚧 BLOCKERS

**✅ No blockers remain.** The one blocker (#0, report chat) is **delivered** — see below.
Everything else in this file is a non-blocking workaround or nice-to-have.

| # | Request | Status |
|---|---------|---|
| **0** | **`POST /api/v1/reports/{id}/chat`** — grounded chat over a report | ✅ **DELIVERED 2026-08-02** — contract honoured exactly. **Frontend confirmed 2026-08-03:** the panel self-enabled with **no code change**, and 13/13 live browser checks passed against the real endpoint (grounded answers with quoted citations, `grounded: false` on off-topic questions, leadership access). Two small reconciliations were made on the frontend side — see [section 0](#0-report-chat-endpoint--blocker). |

---

## Status summary — everything else (non-blocking)

| # | Request | Priority | Blocking? |
|---|---------|:---:|---|
| 1 | Sorting (`sort_by` + `order`) on list endpoints | **High** | No — client-side sort ships, labelled |
| 2 | Per-job tool selection (`input.tools`) | **High** | No — read-only pipeline preview ships |
| 3 | Make `agent_id` actually drive prompt/model | **High** | No — the picker is labelled as provenance-only |
| 4 | Persist the retrieved source passages | **High** | No — but citation markers stay untraceable |
| 5 | Reject unknown query params instead of ignoring them | Medium | No — but it hides bugs like #1 |
| 6 | Expose `audit_logs` via an API endpoint | Medium | No — jobs feed used instead |
| 7 | Report export (DOCX / PDF download) | Medium | No — will block a "download report" button |
| 8 | `q` search + date filters on `GET /jobs` | Low | No |
| 9 | A single dashboard summary/counts endpoint | Low | No — 6 calls used instead |
| 10 | CORS origin for a deployed frontend | Low | Only for non-dev deployment |
| 11 | Clean up leftover test rows | Low | No — cosmetic |

**Already delivered by the backend** (thank you — no action needed):
- ✅ **Report chat** (`POST /api/v1/reports/{id}/chat`) — grounded Q&A over a report.
  Delivered 2026-08-02, honouring the section-0 contract: request `{message, history?}`;
  response `{answer, citations:[{quote, source, section?}], grounded, generated_by}`. Grounds
  on the report content **+ live RAG** over the report's job documents (embeds the question,
  pgvector search). Any authenticated user; **404** unknown report; **422** empty/blank message;
  **503** with a clear detail if the LLM is down (no hallucinated fallback). Stateless — client
  replays `history` (capped to last 20). Verified live (grounded answer with real quoted citations).
- ✅ **Query-param token on the SSE stream** (`GET /jobs/{id}/stream?token=…`), which lets
  the browser's native `EventSource` work. Documented in `FRONTEND.md` §7.

**Considered and NOT required:**
- ❌ **Public registration endpoint** (`POST /auth/register`). The frontend confirmed
  there is none and that `POST /users` is admin-only (401 when anonymous). The product
  decision was that registration is **an administrator creating the account**, which
  also prevents anyone self-assigning a role. No backend change wanted.

---

## 0. Report chat endpoint — ✅ DELIVERED (2026-08-02)

> **Implemented as specified below.** Endpoint: `POST /api/v1/reports/{report_id}/chat`.
> Grounds on report content + live RAG over the report's job documents. Any authenticated
> user; 404/422 as requested; **503** (not a fake answer) when the LLM is down. Stateless.
> The exact request/response shapes below are honoured — the chat UI should self-enable.
>
> **✅ Frontend confirmed, 2026-08-03.** The panel self-enabled with no code change; the
> capability probe found the path on first load. 13/13 live browser checks passed against
> the real endpoint. Two frontend reconciliations were needed after reading the shipped
> contract — neither is a backend problem:
> 1. The message cap was raised from 1000 to **4000** to match `ChatRequest.maxLength`.
> 2. The frontend previously treated a 404 as "endpoint missing" and disabled chat. Now
>    that 404 means *unknown report*, that logic was removed — the OpenAPI probe is the
>    single source of truth for availability, and errors are surfaced as errors.
>
> Observed live: `citations[].source` comes back as `"REPORT"` with the report section in
> `section`, rather than a `[n]` marker. The UI renders whatever is present, so this is
> fine — noting it only so nobody expects the marker to line up with the report's own
> numbered citation list.

### The problem

**There is no chat endpoint anywhere in the API.** Searched all 26 paths for
`chat`, `conversation`, `message`, `ask`, `query`, `qa` — zero matches.

The product README promises the platform "enables interactive chat with the evidence",
and frontend Milestone 14 asks for *"interactive chat linked to report data"* whose
*"responses reference actual report content"*. There is nothing to call.

### What the frontend does today

The report view ships complete (content, citations, versions, provenance). The **chat
panel is fully built** — message thread, input, per-message citations, loading and error
states — but it renders a "chat is not enabled on this backend yet" notice instead of
sending.

**It self-enables.** On load the frontend reads `/openapi.json` and looks for a path
matching `/reports/{…}/chat`. The moment the endpoint exists, chat turns on with **no
frontend change or redeploy** — as long as the shapes below are honoured.

### Requested — `POST /api/v1/reports/{report_id}/chat`

**Stateless is fine for v1** — the client keeps the transcript and replays it. That
avoids new tables and is the fastest route to unblocking the UI. Persisted conversations
can come later without breaking this contract.

**Request body**
```jsonc
{
  "message": "How do the two vendors differ on breach notification?",
  "history": [                                   // optional, oldest first
    { "role": "user",      "content": "…" },
    { "role": "assistant", "content": "…" }
  ]
}
```

**Response body**
```jsonc
{
  "answer": "Vendor A commits to 72 hours; Vendor B's contract does not state a fixed window [2].",
  "citations": [
    {
      "quote": "Vendor A commits to notifying the customer within 72 hours…",
      "source": "[1]",                 // marker, matching the report's own style
      "section": "Breach Notification" // optional: which report section it came from
    }
  ],
  "grounded": true,                    // false when the answer is not supported by the sources
  "generated_by": { "provider": "gemini", "model": "gemini-flash-latest", "usage": { } }
}
```

**Grounding requirements** (this is the part that matters for requirement 3):
- Answer **only** from the report's `content` (summary + sections + citations) and,
  ideally, the chunks of the documents the report's job used.
- When the sources do not support an answer, say so plainly and set `grounded: false`
  rather than inventing one. The frontend renders that state distinctly.
- Always return `citations` for a grounded answer, so the UI can show what backs it.

**Behaviour**
- **RBAC:** any authenticated user (reads are open to all three roles, matching
  `GET /reports/{id}`). If you would rather restrict it to analyst + admin, say so and
  the frontend will gate the panel.
- **404** if the report does not exist. **422** for an empty message.
- Reuse the existing `LLMClient` and its graceful-degradation path — if the provider is
  down, a clear error beats a hallucinated answer.
- Suggested cap: ~20 history messages, and a max message length (the frontend will
  enforce whatever you choose).

**Optional, not required for v1:** token streaming over SSE. The frontend already has
`EventSource` plumbing from the job stream, so it could be adopted later — but a plain
JSON response is enough to unblock, and simpler to build.

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

## 4. Persist the retrieved source passages — **High priority**

### The problem

A report's citations look like `{"claim": "Vendor A notifies within 72 hours…",
"source": "[1]"}` — but **nothing in the API says what `[1]` is**.

I checked whether the marker is resolvable. The retrieval step's recorded output is:

```json
{"top_k": 5, "retrieved": 5, "top_score": 0.6779, "documents_searched": "all"}
```

Counts and metadata — **not the passages**. The research step likewise records
`{"via": "mcp", "sources": 3, "findings": 3}`. `RetrievalTool` writes the passages to
`ctx.input["sources"]`, but that is a working copy (`params = dict(job.input or {})`),
so it never reaches the stored `job.input`. The retrieved text is discarded once the job
finishes.

### Why it matters

Citations that cannot be traced to a source are not really auditable, which undercuts
the platform's compliance story. A reader can see the *claim* but never the evidence
behind it. It also limits the chat endpoint in section 0 — the richest grounding source
is exactly the passages that were retrieved.

### What the frontend does today

Renders each citation's `claim` text with its marker, and links to the job so a reader
can at least see which documents were searched. The marker itself is inert — there is
nothing to link it to.

### Requested

Persist the retrieved passages so a citation marker resolves to real text. Either:

- store them in the retrieval step's `output` (e.g.
  `sources: [{index: 1, document_id, chunk_index, text, score}]`), or
- add them to `report.content.sources` alongside `citations`.

The second is friendlier for the report view, since the report becomes self-contained.
Either way the frontend can then render `[1]` as a link that reveals the quoted passage.

---

## 5. Reject unknown query params — Medium

Related to #1, and the reason it went unnoticed. FastAPI ignores query params it does
not declare, so `?sort_by=title` returns 200 with unsorted data — indistinguishable from
success. A client cannot detect the difference.

**Requested:** reject unrecognised query params with 422 (e.g. a strict dependency or a
`model_config = ConfigDict(extra="forbid")` on the query models). Failing loudly turns a
silent no-op into an obvious error.

---

## 6. Expose `audit_logs` through an API — Medium

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

## 7. Report export — DOCX / PDF download — Medium

Noted as not built in `FRONTEND.md` §9; confirmed no `export` or `download` path exists.
`JobType` already includes an `export` member, so the groundwork is partly there.

**Why it matters:** a cited research report that cannot leave the browser has limited
value to a procurement team. This will block a "Download report" button when the report
detail screen is built.

**Requested:** `GET /api/v1/reports/{id}/export?format=docx|pdf` returning the file with
an appropriate `Content-Disposition`. If generation is slow, returning an `export` job id
and reusing the existing job/SSE machinery would fit the current architecture well.

---

## 8. `q` search and date filters on `GET /jobs` — Low

`GET /jobs` accepts only `status` and `type` — no free-text search, unlike `/reports`,
`/documents`, `/users`, `/agents` and `/tools`, which all have `q`.

**Requested:** add `q` (matching the job's `input.query` text) and optionally
`created_after` / `created_before`. Useful once the jobs screen holds hundreds of rows.

---

## 9. A dashboard summary endpoint — Low

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

## 10. CORS for a deployed frontend — Low

Already noted in `FRONTEND.md` §9. `CORS_ORIGINS` currently allows `http://localhost:4200`.
Any non-dev deployment needs its origin added. **No action needed while developing** —
the Angular dev server proxies `/api` to `:8000`, so requests are same-origin.

---

## 11. Leftover test rows — Low (data, not code)

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
