"""Tool model — a configurable capability the agent can orchestrate."""

from __future__ import annotations

from sqlalchemy import Boolean, Enum, Integer, String, Text, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, SoftDeleteMixin, TimestampMixin, UUIDPrimaryKeyMixin
from app.models.enums import ToolCategory


class Tool(UUIDPrimaryKeyMixin, TimestampMixin, SoftDeleteMixin, Base):
    __tablename__ = "tools"

    # Stable machine key, e.g. "web_research", "pii_redaction".
    key: Mapped[str] = mapped_column(String(100), unique=True, index=True, nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    category: Mapped[ToolCategory] = mapped_column(
        Enum(ToolCategory, name="tool_category", values_callable=lambda e: [m.value for m in e]),
        nullable=False,
    )
    config: Mapped[dict] = mapped_column(JSONB, nullable=False, server_default=text("'{}'::jsonb"))
    enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("true"))
    # Versioning: bumped when the tool's configuration/definition changes.
    version: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("1"))

    def __repr__(self) -> str:  # pragma: no cover
        return f"<Tool {self.key} category={self.category}>"
