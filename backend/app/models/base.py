"""SQLAlchemy declarative base.

All ORM models (added in later milestones) will inherit from ``Base`` so a single
metadata object describes the schema for migrations.
"""

from __future__ import annotations

from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """Shared declarative base for all ORM models."""
