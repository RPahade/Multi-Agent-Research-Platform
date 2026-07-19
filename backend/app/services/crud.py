"""Generic CRUD helpers shared by the entity services (framework-agnostic)."""

from __future__ import annotations

from typing import TypeVar

from sqlalchemy import Select, func, select
from sqlalchemy.orm import Session

T = TypeVar("T")


def paginate(db: Session, stmt: Select, page: int, size: int) -> tuple[list, int]:
    """Return (items, total) for a SELECT statement with limit/offset applied."""
    count_stmt = select(func.count()).select_from(stmt.order_by(None).subquery())
    total = db.scalar(count_stmt) or 0
    items = list(db.scalars(stmt.limit(size).offset((page - 1) * size)))
    return items, total
