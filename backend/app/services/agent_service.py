"""Agent CRUD business logic."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.agent import Agent
from app.services import crud


def list_page(
    db: Session,
    *,
    page: int,
    size: int,
    is_active: bool | None = None,
    q: str | None = None,
) -> tuple[list[Agent], int]:
    stmt = select(Agent).where(Agent.deleted_at.is_(None))
    if is_active is not None:
        stmt = stmt.where(Agent.is_active == is_active)
    if q:
        stmt = stmt.where(Agent.name.ilike(f"%{q}%"))
    stmt = stmt.order_by(Agent.created_at.desc())
    return crud.paginate(db, stmt, page, size)


def create(db: Session, data: dict, *, created_by: uuid.UUID) -> Agent:
    agent = Agent(**data, created_by=created_by)
    db.add(agent)
    db.commit()
    db.refresh(agent)
    return agent


def update(db: Session, agent: Agent, data: dict) -> Agent:
    for field, value in data.items():
        setattr(agent, field, value)
    if data:
        agent.version += 1
    db.commit()
    db.refresh(agent)
    return agent


def soft_delete(db: Session, agent: Agent) -> None:
    agent.deleted_at = datetime.now(timezone.utc)
    db.commit()
