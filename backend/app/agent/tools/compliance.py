"""Compliance / PII redaction tool (Step 1: deterministic stub).

Later milestones: real PII detection + redaction over the report content.
"""

from __future__ import annotations

from app.agent.base import Tool, ToolContext, ToolResult


class ComplianceTool(Tool):
    key = "compliance"
    name = "Redacting PII"
    required = True

    def run(self, ctx: ToolContext) -> ToolResult:
        if self._forced_failure(ctx):
            return ToolResult.failed("forced compliance failure")
        report = ctx.artifacts.get("report", {})
        # Stub: pretend we scanned & redacted the report body.
        redactions = 0
        report["compliance"] = {"pii_redacted": redactions, "scanned": True}
        output = {"pii_redacted": redactions}
        ctx.artifacts["compliance"] = output
        return ToolResult.ok(output)
