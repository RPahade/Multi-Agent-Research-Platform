"""add job idempotency & resilience columns (Milestone 5 - step 2)

Revision ID: 0003_job_resilience
Revises: 0002_refresh_tokens
Create Date: 2026-07-19
"""
from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0003_job_resilience"
down_revision: str | None = "0002_refresh_tokens"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("jobs", sa.Column("idempotency_key", sa.String(length=64), nullable=True))
    op.add_column("jobs", sa.Column("attempts", sa.Integer(), server_default=sa.text("0"), nullable=False))
    op.add_column("jobs", sa.Column("max_attempts", sa.Integer(), server_default=sa.text("3"), nullable=False))
    op.add_column("jobs", sa.Column("last_heartbeat", sa.DateTime(timezone=True), nullable=True))
    # Idempotency is scoped per user; only enforced when a key is provided.
    op.create_index(
        "uq_jobs_user_idempotency",
        "jobs",
        ["user_id", "idempotency_key"],
        unique=True,
        postgresql_where=sa.text("idempotency_key IS NOT NULL"),
    )


def downgrade() -> None:
    op.drop_index("uq_jobs_user_idempotency", table_name="jobs")
    op.drop_column("jobs", "last_heartbeat")
    op.drop_column("jobs", "max_attempts")
    op.drop_column("jobs", "attempts")
    op.drop_column("jobs", "idempotency_key")
