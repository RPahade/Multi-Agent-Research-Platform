"""Smoke tests for the health endpoints.

These do not require a running database: creating the SQLAlchemy engine is lazy,
and ``/health`` never touches the DB. The DB readiness endpoint is covered
end-to-end via docker-compose (see README).
"""

from __future__ import annotations

from fastapi.testclient import TestClient

from app.core.config import settings
from app.main import app

client = TestClient(app)


def test_root_returns_service_metadata() -> None:
    response = client.get("/")
    assert response.status_code == 200
    body = response.json()
    assert body["service"] == settings.app_name
    assert body["docs"] == "/docs"


def test_health_liveness() -> None:
    response = client.get(f"{settings.api_v1_prefix}/health")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["app"] == settings.app_name
    assert body["version"] == settings.app_version


def test_openapi_schema_available() -> None:
    response = client.get("/openapi.json")
    assert response.status_code == 200
    assert response.json()["info"]["title"] == settings.app_name
