"""Citation verification tool (Step 1: deterministic stub). Optional tool.

Later milestones: verify each claim maps to a real source; flag unverifiable claims.
"""

from __future__ import annotations

from app.agent.base import Tool, ToolContext, ToolResult


class CitationTool(Tool):
    key = "citation"
    name = "Verifying citations"
    required = False  # optional: a failure here degrades gracefully

    def run(self, ctx: ToolContext) -> ToolResult:
        if self._forced_failure(ctx):
            return ToolResult.failed("forced citation failure")
        findings = ctx.artifacts.get("research", {}).get("findings", [])
        output = {"verified": len(findings), "unverified": 0}
        ctx.artifacts["citation"] = output
        return ToolResult.ok(output)
