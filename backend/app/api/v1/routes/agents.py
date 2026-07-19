"""Agent CRUD endpoints. Reads: any authenticated user. Writes: admin only."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, Query, Response, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, require_admin
from app.api.utils import get_active_or_404
from app.db.session import get_db
from app.models.agent import Agent
from app.models.user import User
from app.schemas.agent import AgentCreate, AgentRead, AgentUpdate
from app.schemas.common import Page, PageParams
from app.services import agent_service

router = APIRouter(prefix="/agents", tags=["agents"])


@router.get("", response_model=Page[AgentRead], summary="List agents")
def list_agents(
    pg: PageParams = Depends(),
    is_active: bool | None = Query(default=None),
    q: str | None = Query(default=None, description="search name"),
    db: Session = Depends(get_db),
    _user: User = Depends(get_current_user),
) -> Page[AgentRead]:
    items, total = agent_service.list_page(db, page=pg.page, size=pg.size, is_active=is_active, q=q)
    return Page[AgentRead].create([AgentRead.model_validate(a) for a in items], total, pg)


@router.get("/{agent_id}", response_model=AgentRead, summary="Get an agent")
def get_agent(
    agent_id: uuid.UUID,
    db: Session = Depends(get_db),
    _user: User = Depends(get_current_user),
) -> Agent:
    return get_active_or_404(db, Agent, agent_id, "Agent")


@router.post("", response_model=AgentRead, status_code=status.HTTP_201_CREATED, summary="Create an agent")
def create_agent(
    payload: AgentCreate,
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin),
) -> Agent:
    return agent_service.create(db, payload.model_dump(), created_by=admin.id)


@router.patch("/{agent_id}", response_model=AgentRead, summary="Update an agent")
def update_agent(
    agent_id: uuid.UUID,
    payload: AgentUpdate,
    db: Session = Depends(get_db),
    _admin: User = Depends(require_admin),
) -> Agent:
    agent = get_active_or_404(db, Agent, agent_id, "Agent")
    return agent_service.update(db, agent, payload.model_dump(exclude_unset=True))


@router.delete("/{agent_id}", status_code=status.HTTP_204_NO_CONTENT, summary="Delete an agent (soft)")
def delete_agent(
    agent_id: uuid.UUID,
    db: Session = Depends(get_db),
    _admin: User = Depends(require_admin),
) -> Response:
    agent = get_active_or_404(db, Agent, agent_id, "Agent")
    agent_service.soft_delete(db, agent)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
