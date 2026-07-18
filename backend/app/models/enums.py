"""Enumerated types shared across the ORM models.

Each becomes a native PostgreSQL ``ENUM`` type. Values are the lowercase strings
stored in the database (see ``values_callable`` usage in the models).
"""

from __future__ import annotations

import enum


class UserRole(str, enum.Enum):
    """Role-based access control roles."""

    ANALYST = "analyst"
    ADMIN = "admin"
    LEADERSHIP = "leadership"


class ToolCategory(str, enum.Enum):
    """The categories of tools the agent can orchestrate."""

    RETRIEVAL = "retrieval"          # document ingestion & retrieval
    WEB_RESEARCH = "web_research"    # external web research
    CITATION = "citation"           # citation verification
    EXPORT = "export"               # formatting & exporting (DOCX/PDF)
    COMPLIANCE = "compliance"       # PII redaction / compliance


class JobType(str, enum.Enum):
    """Kinds of long-running background jobs."""

    RESEARCH = "research"
    INGESTION = "ingestion"
    EXPORT = "export"


class JobStatus(str, enum.Enum):
    """Lifecycle status of a job."""

    PENDING = "pending"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    CANCELLED = "cancelled"


class ReportStatus(str, enum.Enum):
    """Lifecycle status of a report."""

    DRAFT = "draft"
    FINAL = "final"
    ARCHIVED = "archived"
