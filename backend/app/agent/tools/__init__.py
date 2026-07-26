"""Concrete tools and the ordered pipeline the agent runs.

Milestone 6 step 2: the report is written by the LLM-powered SynthesisTool
(with a deterministic fallback). FormattingTool is retained for the future
export (DOCX/PDF) milestone and is not currently in the pipeline.
"""

from __future__ import annotations

from app.agent.base import Tool
from app.agent.tools.citation import CitationTool
from app.agent.tools.compliance import ComplianceTool
from app.agent.tools.research import ResearchTool
from app.agent.tools.retrieval import RetrievalTool
from app.agent.tools.synthesis import SynthesisTool
from app.core.config import settings


def build_pipeline() -> list[Tool]:
    """The sequential order in which the agent invokes tools.

    When MCP is enabled, the self-contained tools (research/citation/compliance) are
    served by the MCP server (with local fallback); retrieval + synthesis stay local.
    """
    research: Tool = ResearchTool()
    citation: Tool = CitationTool()
    compliance: Tool = ComplianceTool()

    if settings.mcp_enabled:
        from app.agent.mcp.tools import MCPCitationTool, MCPComplianceTool, MCPResearchTool

        research = MCPResearchTool(research)
        citation = MCPCitationTool(citation)
        compliance = MCPComplianceTool(compliance)

    return [
        RetrievalTool(),   # RAG: embed query -> top-K chunks (local; needs pgvector)
        research,
        SynthesisTool(),   # LLM writes the report (local; core LLM call)
        citation,
        compliance,
    ]
