"""The Tool contract every tool obeys.

This is the seam that keeps orchestration decoupled from tool implementation: local
Python tools implement `Tool` today; an `MCPTool` adapter will implement the same
interface later, and the orchestrator won't change.
"""

from __future__ import annotations

import uuid
from abc import ABC, abstractmethod
from dataclasses import dataclass, field


@dataclass
class ToolContext:
    """Shared state threaded through the pipeline.

    Tools read ``input`` (the job's parameters) and prior tools' ``artifacts``,
    and write their own results back into ``artifacts`` for downstream tools.
    """

    job_id: uuid.UUID
    user_id: uuid.UUID | None
    input: dict
    artifacts: dict = field(default_factory=dict)


@dataclass
class ToolResult:
    status: str  # "succeeded" | "failed" | "skipped"
    output: dict | None = None
    error: str | None = None

    @classmethod
    def ok(cls, output: dict | None = None) -> "ToolResult":
        return cls(status="succeeded", output=output or {})

    @classmethod
    def failed(cls, error: str) -> "ToolResult":
        return cls(status="failed", error=error)


class Tool(ABC):
    """Base class for a single agent tool."""

    #: stable machine key (matches the M4 tools registry keys)
    key: str = ""
    #: human-friendly step label (shown as the job's current_step)
    name: str = ""
    #: if a required tool fails, the pipeline stops; optional failures are tolerated
    required: bool = True

    @abstractmethod
    def run(self, ctx: ToolContext) -> ToolResult:
        """Do the work and return a result. May raise; the orchestrator will catch it."""

    def _forced_failure(self, ctx: ToolContext) -> bool:
        """Test hook: ``input.fail_tool == self.key`` forces this tool to fail."""
        return ctx.input.get("fail_tool") == self.key
