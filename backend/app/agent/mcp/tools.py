"""MCP-backed tool adapters.

Each wraps a local tool of the same ``key`` and forwards ``run()`` to the MCP
server. If the server is unreachable, it transparently falls back to the local
tool — so enabling MCP never makes the pipeline less reliable.
"""

from __future__ import annotations

import logging

from app.agent.base import Tool, ToolContext, ToolResult
from app.agent.mcp import client as mcp_client
from app.agent.mcp.client import MCPUnavailable

logger = logging.getLogger(__name__)


class MCPTool(Tool):
    mcp_tool_name: str = ""

    def __init__(self, local_fallback: Tool) -> None:
        self.local = local_fallback

    def build_args(self, ctx: ToolContext) -> dict:  # pragma: no cover - overridden
        return {}

    def apply_result(self, ctx: ToolContext, data: dict) -> dict:  # pragma: no cover - overridden
        return {}

    def run(self, ctx: ToolContext) -> ToolResult:
        try:
            data = mcp_client.call(self.mcp_tool_name, self.build_args(ctx))
        except MCPUnavailable as exc:
            logger.warning("MCP tool '%s' unavailable (%s); using local fallback", self.mcp_tool_name, exc)
            result = self.local.run(ctx)
            if result.output is not None:
                result.output = {**result.output, "via": "local-fallback", "mcp_error": str(exc)[:200]}
            return result
        return ToolResult.ok({**self.apply_result(ctx, data), "via": "mcp"})


class MCPResearchTool(MCPTool):
    key = "research"
    name = "Researching sources"
    required = True
    mcp_tool_name = "web_research"

    def build_args(self, ctx: ToolContext) -> dict:
        return {"query": ctx.input.get("query") or "the requested topic"}

    def apply_result(self, ctx: ToolContext, data: dict) -> dict:
        ctx.artifacts["research"] = data
        return {"findings": len(data.get("findings", [])), "sources": data.get("sources")}


class MCPCitationTool(MCPTool):
    key = "citation"
    name = "Verifying citations"
    required = False
    mcp_tool_name = "verify_citations"

    def build_args(self, ctx: ToolContext) -> dict:
        return {"findings": ctx.artifacts.get("research", {}).get("findings", [])}

    def apply_result(self, ctx: ToolContext, data: dict) -> dict:
        ctx.artifacts["citation"] = data
        return dict(data)


class MCPComplianceTool(MCPTool):
    key = "compliance"
    name = "Redacting PII"
    required = True
    mcp_tool_name = "redact_pii"

    def build_args(self, ctx: ToolContext) -> dict:
        return {"report": ctx.artifacts.get("report", {})}

    def apply_result(self, ctx: ToolContext, data: dict) -> dict:
        if isinstance(data.get("report"), dict):
            ctx.artifacts["report"] = data["report"]
        redactions = int(data.get("pii_redacted", 0))
        ctx.artifacts["compliance"] = {"pii_redacted": redactions}
        return {"pii_redacted": redactions}
