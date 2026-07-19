"""Tool CRUD business logic."""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.models.enums import ToolCategory
from app.models.tool import Tool
from app.services import crud


def get_by_key(db: Session, key: str) -> Tool | None:
    return db.scalar(select(Tool).where(Tool.key == key, Tool.deleted_at.is_(None)))


def list_page(
    db: Session,
    *,
    page: int,
    size: int,
    category: ToolCategory | None = None,
    enabled: bool | None = None,
    q: str | None = None,
) -> tuple[list[Tool], int]:
    stmt = select(Tool).where(Tool.deleted_at.is_(None))
    if category is not None:
        stmt = stmt.where(Tool.category == category)
    if enabled is not None:
        stmt = stmt.where(Tool.enabled == enabled)
    if q:
        like = f"%{q}%"
        stmt = stmt.where(or_(Tool.key.ilike(like), Tool.name.ilike(like)))
    stmt = stmt.order_by(Tool.created_at.desc())
    return crud.paginate(db, stmt, page, size)


def create(db: Session, data: dict) -> Tool:
    tool = Tool(**data)
    db.add(tool)
    db.commit()
    db.refresh(tool)
    return tool


def update(db: Session, tool: Tool, data: dict) -> Tool:
    for field, value in data.items():
        setattr(tool, field, value)
    if data:
        tool.version += 1
    db.commit()
    db.refresh(tool)
    return tool


def soft_delete(db: Session, tool: Tool) -> None:
    tool.deleted_at = datetime.now(timezone.utc)
    db.commit()
