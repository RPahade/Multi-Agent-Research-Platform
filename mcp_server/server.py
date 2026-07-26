"""Standalone MCP server exposing the platform's self-contained research tools.

This is a separate service (its own container) that advertises tools over the
Model Context Protocol (Streamable HTTP). The backend connects to it as an MCP
*client* and calls these tools through the same `Tool` interface as local tools.

Exposes:
  - web_research(query)      : gather findings for a query (stub; real search later)
  - verify_citations(...)    : check claims map to sources
  - redact_pii(report)       : real regex-based PII redaction over report text
"""

from __future__ import annotations

import re

from mcp.server.fastmcp import FastMCP

mcp = FastMCP("mari-research-tools", host="0.0.0.0", port=8090)


@mcp.tool()
def web_research(query: str) -> dict:
    """Return preliminary research findings for a query."""
    q = query or "the requested topic"
    findings = [
        f"Finding 1 about {q} (via MCP)",
        f"Finding 2 about {q} (via MCP)",
        f"Finding 3 about {q} (via MCP)",
    ]
    return {"query": q, "sources": 3, "findings": findings}


@mcp.tool()
def verify_citations(findings: list[str] | None = None) -> dict:
    """Verify that findings/claims are backed by sources."""
    findings = findings or []
    return {"verified": len(findings), "unverified": 0}


# --- PII redaction (a genuinely useful, deterministic tool) ---

_PATTERNS: list[tuple[str, re.Pattern]] = [
    ("EMAIL", re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")),
    ("SSN", re.compile(r"\b\d{3}-\d{2}-\d{4}\b")),
    ("CARD", re.compile(r"\b(?:\d[ -]?){13,16}\b")),
    ("PHONE", re.compile(r"\b(?:\+?\d[\s-]?){9,14}\d\b")),
]


def _redact_text(text: str) -> tuple[str, int]:
    count = 0
    for tag, pattern in _PATTERNS:  # order matters: SSN/CARD before PHONE
        def _sub(_m: re.Match, _tag: str = tag) -> str:
            nonlocal count
            count += 1
            return f"[REDACTED-{_tag}]"

        text = pattern.sub(_sub, text)
    return text, count


@mcp.tool()
def redact_pii(report: dict) -> dict:
    """Redact emails/phones/SSNs/card numbers from a report's text fields."""
    total = 0

    def walk(obj):
        nonlocal total
        if isinstance(obj, str):
            redacted, n = _redact_text(obj)
            total += n
            return redacted
        if isinstance(obj, list):
            return [walk(x) for x in obj]
        if isinstance(obj, dict):
            return {k: walk(v) for k, v in obj.items()}
        return obj

    redacted_report = walk(report or {})
    if isinstance(redacted_report, dict):
        redacted_report["compliance"] = {"pii_redacted": total, "scanned": True}
    return {"pii_redacted": total, "report": redacted_report}


if __name__ == "__main__":
    mcp.run(transport="streamable-http")
