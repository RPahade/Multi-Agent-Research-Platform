"""Tool CRUD endpoints. Reads: any authenticated user. Writes: admin only."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, require_admin
from app.api.utils import get_active_or_404
from app.db.session import get_db
from app.models.enums import ToolCategory
from app.models.tool import Tool
from app.models.user import User
from app.schemas.common import Page, PageParams
from app.schemas.tool import ToolCreate, ToolRead, ToolUpdate
from app.services import tool_service

router = APIRouter(prefix="/tools", tags=["tools"])


@router.get("", response_model=Page[ToolRead], summary="List tools")
def list_tools(
    pg: PageParams = Depends(),
    category: ToolCategory | None = Query(default=None),
    enabled: bool | None = Query(default=None),
    q: str | None = Query(default=None, description="search key/name"),
    db: Session = Depends(get_db),
    _user: User = Depends(get_current_user),
) -> Page[ToolRead]:
    items, total = tool_service.list_page(
        db, page=pg.page, size=pg.size, category=category, enabled=enabled, q=q
    )
    return Page[ToolRead].create([ToolRead.model_validate(t) for t in items], total, pg)


@router.get("/{tool_id}", response_model=ToolRead, summary="Get a tool")
def get_tool(
    tool_id: uuid.UUID,
    db: Session = Depends(get_db),
    _user: User = Depends(get_current_user),
) -> Tool:
    return get_active_or_404(db, Tool, tool_id, "Tool")


@router.post("", response_model=ToolRead, status_code=status.HTTP_201_CREATED, summary="Create a tool")
def create_tool(
    payload: ToolCreate,
    db: Session = Depends(get_db),
    _admin: User = Depends(require_admin),
) -> Tool:
    if tool_service.get_by_key(db, payload.key) is not None:
        raise HTTPException(status.HTTP_409_CONFLICT, "A tool with this key already exists")
    return tool_service.create(db, payload.model_dump())


@router.patch("/{tool_id}", response_model=ToolRead, summary="Update a tool")
def update_tool(
    tool_id: uuid.UUID,
    payload: ToolUpdate,
    db: Session = Depends(get_db),
    _admin: User = Depends(require_admin),
) -> Tool:
    tool = get_active_or_404(db, Tool, tool_id, "Tool")
    return tool_service.update(db, tool, payload.model_dump(exclude_unset=True))


@router.delete("/{tool_id}", status_code=status.HTTP_204_NO_CONTENT, summary="Delete a tool (soft)")
def delete_tool(
    tool_id: uuid.UUID,
    db: Session = Depends(get_db),
    _admin: User = Depends(require_admin),
) -> Response:
    tool = get_active_or_404(db, Tool, tool_id, "Tool")
    tool_service.soft_delete(db, tool)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
