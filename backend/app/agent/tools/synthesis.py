"""Synthesis tool (Milestone 6, step 2) — LLM writes the structured report.

Uses the configured LLM provider to turn the query + provided sources into a cited
report (JSON). Falls back to a deterministic stub report if no provider is configured
or the LLM keeps failing, so the pipeline never hard-fails on LLM issues.
"""

from __future__ import annotations

import logging

from app.agent.base import Tool, ToolContext, ToolResult
from app.agent.llm import LLMError, get_llm_client
from app.core.config import settings

logger = logging.getLogger(__name__)

_SYSTEM = (
    "You are a meticulous procurement & strategy research analyst. "
    "Write a concise, well-structured research report answering the user's query. "
    "Ground every claim ONLY in the provided sources and cite them by their [n] index; "
    "if the sources are insufficient, say so rather than inventing facts. "
    "Return ONLY JSON with this shape: "
    '{"title": str, "summary": str, '
    '"sections": [{"heading": str, "body": str}], '
    '"citations": [{"claim": str, "source": str}]}'
)


class SynthesisTool(Tool):
    key = "synthesis"
    name = "Synthesizing report"
    required = True

    def run(self, ctx: ToolContext) -> ToolResult:
        if self._forced_failure(ctx):
            return ToolResult.failed("forced synthesis failure")

        query = ctx.input.get("query") or "the requested topic"
        sources = ctx.input.get("sources") or []

        client = get_llm_client()
        if client is None:
            return self._fallback(ctx, query, sources, "LLM provider not configured")

        try:
            resp = client.generate_json(
                _SYSTEM,
                self._build_prompt(query, sources, ctx),
                temperature=settings.llm_temperature,
                max_tokens=settings.llm_max_tokens,
            )
        except LLMError as exc:
            logger.warning("LLM synthesis failed (%s); falling back to stub report", exc)
            return self._fallback(ctx, query, sources, f"LLM error: {exc}")

        report = self._normalize(resp.data, query)
        report["generated_by"] = {"provider": client.provider, "model": client.model, "usage": resp.usage}
        ctx.artifacts["report"] = report
        return ToolResult.ok(
            {"provider": client.provider, "model": client.model,
             "title": report.get("title"), "usage": resp.usage}
        )

    # --- helpers ---

    @staticmethod
    def _build_prompt(query: str, sources: list, ctx: ToolContext) -> str:
        lines = [f"Research query: {query}", ""]
        if sources:
            lines.append("Sources:")
            for i, s in enumerate(sources, start=1):
                title = s.get("title", f"Source {i}") if isinstance(s, dict) else f"Source {i}"
                text = s.get("text", "") if isinstance(s, dict) else str(s)
                lines.append(f"[{i}] {title}: {text}")
        else:
            lines.append("(No sources provided; note this limitation in the report.)")
        findings = ctx.artifacts.get("research", {}).get("findings")
        if findings:
            lines += ["", "Preliminary findings:"] + [f"- {f}" for f in findings]
        lines += ["", "Write the report as JSON now."]
        return "\n".join(lines)

    @staticmethod
    def _normalize(data: dict, query: str) -> dict:
        if not isinstance(data, dict):
            data = {}
        sections = data.get("sections")
        if not isinstance(sections, list):
            sections = [{"heading": "Report", "body": str(data)}]
        return {
            "title": data.get("title") or f"Research Report: {query}",
            "summary": data.get("summary"),
            "sections": sections,
            "citations": data.get("citations", []),
        }

    def _fallback(self, ctx: ToolContext, query: str, sources: list, reason: str) -> ToolResult:
        findings = ctx.artifacts.get("research", {}).get("findings", [])
        report = {
            "title": f"Research Report: {query}",
            "summary": f"Automated (stub) report on '{query}'.",
            "sections": [
                {"heading": "Overview", "body": f"This report summarizes research on {query}."},
                {"heading": "Findings", "body": "; ".join(findings) or "No findings available."},
            ],
            "citations": [{"claim": "source-provided", "source": s.get("title", "source")}
                          for s in sources if isinstance(s, dict)],
            "degraded": True,
            "degraded_reason": reason,
        }
        ctx.artifacts["report"] = report
        return ToolResult.ok({"fallback": True, "reason": reason, "title": report["title"]})
