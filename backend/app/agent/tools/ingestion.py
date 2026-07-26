"""Document ingestion & retrieval tool (Step 1: deterministic stub).

Later milestones: real PDF/DOCX parsing + chunking + embeddings (RAG).
"""

from __future__ import annotations

from app.agent.base import Tool, ToolContext, ToolResult


class IngestionTool(Tool):
    key = "ingestion"
    name = "Ingesting documents"
    required = True

    def run(self, ctx: ToolContext) -> ToolResult:
        if self._forced_failure(ctx):
            return ToolResult.failed("forced ingestion failure")
        documents = ctx.input.get("documents") or ["sample.pdf"]
        output = {"documents": len(documents), "chunks": len(documents) * 12}
        ctx.artifacts["ingestion"] = output
        return ToolResult.ok(output)
