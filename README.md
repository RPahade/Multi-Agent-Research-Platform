# Multi-Agent Research Intelligence Platform

A research agent platform for Procurement & Strategy teams. It ingests large
documents (PDF, DOCX), performs web and internal research via configurable tools,
synthesises **cited** reports, enables interactive chat with the evidence, and
produces **auditable logs** for compliance.

One orchestrating **agent** drives a toolbox:
document ingestion & retrieval · web research · citation verification ·
formatting & exporting · compliance (PII redaction).

> **Status:** Milestone 1 — project setup. Backend skeleton + PostgreSQL, runnable
> via Docker. Later milestones add the agent, tools, async tasks, Kafka, Langfuse,
> exporters, and the Angular frontend.

## Tech stack

| Layer         | Technology                                  |
|---------------|---------------------------------------------|
| Backend       | FastAPI (Python 3.12)                        |
| Database      | PostgreSQL 16                               |
| Messaging     | Kafka (local) — *later milestone*           |
| Observability | Langfuse — *later milestone*                |
| Frontend      | Angular — *later milestone*                  |
| Infra         | Docker & docker-compose (local deployment)  |

## Repository layout

```
.
├── docker-compose.yml        # orchestrates backend + db (+ future services)
├── .env.example              # copy to .env
├── backend/                  # FastAPI service
│   ├── Dockerfile
│   ├── requirements.txt
│   ├── app/
│   │   ├── main.py           # app factory + FastAPI instance
│   │   ├── core/             # config + logging
│   │   ├── api/v1/           # versioned routes (health, ...)
│   │   ├── db/               # engine + session
│   │   ├── models/           # SQLAlchemy ORM (Base for now)
│   │   ├── schemas/          # Pydantic request/response models
│   │   └── services/         # business logic (added per feature)
│   └── tests/                # pytest smoke tests
└── frontend/                 # Angular app (later milestone)
```

## Prerequisites

- [Docker](https://docs.docker.com/get-docker/) & Docker Compose v2
- (Optional, for running the backend without Docker) Python 3.12

## Quick start (Docker)

```bash
# 1. Create your local env file
cp .env.example .env

# 2. Build and start backend + database
docker compose up --build

# 3. Open the interactive API docs
#    http://localhost:8000/docs
```

Verify it's alive:

| Endpoint                              | Expected                                   |
|---------------------------------------|--------------------------------------------|
| `GET http://localhost:8000/`          | service metadata + docs link               |
| `GET http://localhost:8000/api/v1/health`     | `{"status":"ok", ...}`             |
| `GET http://localhost:8000/api/v1/health/db`  | `{"status":"ok","database":"reachable"}` |
| `http://localhost:8000/docs`          | Swagger UI (OpenAPI)                        |

Stop and remove containers:

```bash
docker compose down          # keep the database volume
docker compose down -v       # also delete the database volume
```

## Running the backend locally (without Docker)

```bash
cd backend
python -m venv .venv
# Windows: .venv\Scripts\activate   |   macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt

# Point at a local Postgres (or the docker one) — note host "localhost":
export DATABASE_URL="postgresql+psycopg://postgres:postgres@localhost:5432/research"

uvicorn app.main:app --reload
```

## Tests

```bash
cd backend
pip install -r requirements.txt
pytest
```

## Configuration

All settings come from environment variables (see `.env.example`), read via
`app/core/config.py`. Key variables: `APP_NAME`, `ENV`, `LOG_LEVEL`,
`API_V1_PREFIX`, `CORS_ORIGINS`, `DATABASE_URL`, and the `POSTGRES_*` credentials.
