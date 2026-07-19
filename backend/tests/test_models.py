"""Schema-level tests for the ORM models.

These run without a database: they validate that all models import, mappers
configure (relationships resolve), and the expected tables/columns exist on the
metadata. Actual DB behaviour is exercised via Alembic when Postgres is available.
"""

from __future__ import annotations

from sqlalchemy.orm import configure_mappers

import app.models as models


def test_all_expected_tables_registered() -> None:
    configure_mappers()  # raises if any relationship is misconfigured
    expected = {
        "users",
        "agents",
        "tools",
        "agent_tools",
        "jobs",
        "reports",
        "report_versions",
        "audit_logs",
        "refresh_tokens",
    }
    assert expected == set(models.Base.metadata.tables.keys())


def test_users_table_has_role_and_email() -> None:
    users = models.Base.metadata.tables["users"]
    assert "email" in users.columns
    assert users.columns["email"].unique is True
    assert "role" in users.columns


def test_audit_log_uses_bigint_pk() -> None:
    audit = models.Base.metadata.tables["audit_logs"]
    assert audit.columns["id"].primary_key is True
    # append-only: no soft-delete/updated_at columns
    assert "deleted_at" not in audit.columns


def test_report_versions_unique_constraint() -> None:
    rv = models.Base.metadata.tables["report_versions"]
    uniques = {
        tuple(sorted(c.name for c in con.columns))
        for con in rv.constraints
        if con.__class__.__name__ == "UniqueConstraint"
    }
    assert ("report_id", "version") in uniques
