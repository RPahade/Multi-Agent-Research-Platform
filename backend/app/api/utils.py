"""Small API-layer helpers."""

from __future__ import annotations

from typing import TypeVar

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

T = TypeVar("T")


def get_active_or_404(db: Session, model: type[T], obj_id, name: str) -> T:
    """Fetch a row by id, treating soft-deleted rows as absent; raise 404 otherwise."""
    obj = db.get(model, obj_id)
    if obj is None or getattr(obj, "deleted_at", None) is not None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=f"{name} not found"
        )
    return obj
