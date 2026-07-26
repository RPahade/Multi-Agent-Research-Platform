"""MCP status endpoint — shows whether the MCP server is enabled/reachable and its tools."""

from __future__ import annotations

from fastapi import APIRouter, Depends

from app.agent.mcp import client as mcp_client
from app.api.deps import get_current_user
from app.models.user import User

router = APIRouter(prefix="/mcp", tags=["mcp"])


@router.get("/status", summary="MCP server status and available tools")
def mcp_status(_user: User = Depends(get_current_user)) -> dict:
    return mcp_client.status()
