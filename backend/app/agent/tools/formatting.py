"""Formatting tool (Step 1: deterministic stub).

Assembles the structured report body from prior tools' artifacts. Later milestones:
real DOCX/PDF export + LLM-written prose.
"""

from __future__ import annotations

from app.agent.base import Tool, ToolContext, ToolResult


class FormattingTool(Tool):
    key = "formatting"
    name = "Formatting report"
    required = True

    def run(self, ctx: ToolContext) -> ToolResult:
        if self._forced_failure(ctx):
            return ToolResult.failed("forced formatting failure")
        research = ctx.artifacts.get("research", {})
        citation = ctx.artifacts.get("citation", {})
        ingestion = ctx.artifacts.get("ingestion", {})
        query = research.get("query", "the requested topic")

        content = {
            "title": f"Research Report: {query}",
            "summary": f"Automated research report on '{query}'.",
            "sections": [
                {"heading": "Overview", "body": f"This report summarizes research on {query}."},
                {"heading": "Findings", "items": research.get("findings", [])},
                {
                    "heading": "Evidence",
                    "documents_ingested": ingestion.get("documents", 0),
                    "chunks": ingestion.get("chunks", 0),
                    "sources": research.get("sources", 0),
                },
            ],
            "citations": citation or {"verified": 0, "unverified": 0},
        }
        ctx.artifacts["report"] = content
        return ToolResult.ok({"title": content["title"], "sections": len(content["sections"])})
