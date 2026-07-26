"""add job_steps table (Milestone 6 - agent orchestration, step 1)

Revision ID: 0004_job_steps
Revises: 0003_job_resilience
Create Date: 2026-07-19
"""
from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "0004_job_steps"
down_revision: str | None = "0003_job_resilience"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

job_step_status = postgresql.ENUM(
    "pending", "running", "succeeded", "failed", "skipped",
    name="job_step_status", create_type=False,
)


def upgrade() -> None:
    job_step_status.create(op.get_bind(), checkfirst=True)
    op.create_table(
        "job_steps",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("job_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("sequence", sa.Integer(), nullable=False),
        sa.Column("tool_key", sa.String(length=100), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("required", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column("status", job_step_status, server_default=sa.text("'pending'::job_step_status"), nullable=False),
        sa.Column("output", postgresql.JSONB(), nullable=True),
        sa.Column("error", sa.Text(), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["job_id"], ["jobs.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("job_id", "sequence", name="uq_job_step_sequence"),
    )
    op.create_index("ix_job_steps_job_id", "job_steps", ["job_id"])


def downgrade() -> None:
    op.drop_index("ix_job_steps_job_id", table_name="job_steps")
    op.drop_table("job_steps")
    job_step_status.drop(op.get_bind(), checkfirst=True)
