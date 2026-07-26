"""Web/internal research tool (Step 1: deterministic stub).

Later milestones: real web search + retrieval over ingested chunks, LLM synthesis.
"""

from __future__ import annotations

from app.agent.base import Tool, ToolContext, ToolResult


class ResearchTool(Tool):
    key = "research"
    name = "Researching sources"
    required = True

    def run(self, ctx: ToolContext) -> ToolResult:
        if self._forced_failure(ctx):
            return ToolResult.failed("forced research failure")
        query = ctx.input.get("query") or "the requested topic"
        findings = [
            f"Finding 1 about {query}",
            f"Finding 2 about {query}",
            f"Finding 3 about {query}",
        ]
        output = {"query": query, "sources": 3, "findings": findings}
        ctx.artifacts["research"] = output
        return ToolResult.ok(output)
