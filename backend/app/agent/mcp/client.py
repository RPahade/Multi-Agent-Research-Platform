"""Thin, synchronous wrapper over the async MCP client SDK.

Our job workers are synchronous threads, so each call opens a short-lived
Streamable-HTTP session via ``asyncio.run``. The MCP SDK is imported lazily so the
app still starts if the SDK/server is unavailable (calls then fall back to local tools).
"""

from __future__ import annotations

import asyncio
import json
import logging

from app.core.config import settings

logger = logging.getLogger(__name__)


class MCPUnavailable(Exception):
    """Raised when the MCP server can't be reached or a tool call fails."""


def _extract(result) -> dict:
    """Pull a JSON dict out of an MCP CallToolResult (text block or structured)."""
    if getattr(result, "isError", False):
        raise MCPUnavailable(f"tool error: {getattr(result, 'content', None)}")
    for block in getattr(result, "content", None) or []:
        text = getattr(block, "text", None)
        if text:
            try:
                return json.loads(text)
            except (ValueError, TypeError):
                continue
    data = getattr(result, "structuredContent", None)
    if isinstance(data, dict):
        return data
    return {}


async def _with_session(coro_fn):
    from mcp import ClientSession
    from mcp.client.streamable_http import streamablehttp_client

    async with streamablehttp_client(settings.mcp_server_url) as (read, write, *_):
        async with ClientSession(read, write) as session:
            await session.initialize()
            return await coro_fn(session)


def _run(coro_fn):
    try:
        return asyncio.run(asyncio.wait_for(_with_session(coro_fn), timeout=settings.mcp_timeout_seconds))
    except MCPUnavailable:
        raise
    except Exception as exc:  # noqa: BLE001 - any transport/timeout error → unavailable
        raise MCPUnavailable(f"{type(exc).__name__}: {exc}") from exc


def call(tool_name: str, arguments: dict) -> dict:
    """Call a tool on the MCP server and return its JSON result."""
    async def _do(session):
        return _extract(await session.call_tool(tool_name, arguments))

    return _run(_do)


def list_tool_names() -> list[str]:
    async def _do(session):
        res = await session.list_tools()
        return [t.name for t in res.tools]

    return _run(_do)


def status() -> dict:
    """Report whether the MCP server is enabled and reachable, and its tools."""
    info = {"enabled": settings.mcp_enabled, "server_url": settings.mcp_server_url, "reachable": False, "tools": []}
    if not settings.mcp_enabled:
        return info
    try:
        info["tools"] = list_tool_names()
        info["reachable"] = True
    except MCPUnavailable as exc:
        info["error"] = str(exc)
    return info
