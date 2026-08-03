"""Pydantic schemas for grounded report chat."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.core.config import settings


class ChatMessage(BaseModel):
    role: str = Field(description='"user" or "assistant"')
    content: str


class ChatRequest(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "message": "How do the two vendors differ on breach notification?",
                    "history": [
                        {"role": "user", "content": "Which vendor stores data in the EU?"},
                        {"role": "assistant", "content": "Vendor B stores data in the EU (Frankfurt, Dublin) [1]."},
                    ],
                }
            ]
        }
    )

    message: str = Field(min_length=1, max_length=settings.chat_message_max_chars)
    history: list[ChatMessage] = Field(default_factory=list)

    @field_validator("message")
    @classmethod
    def _not_blank(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("message must not be blank")
        return v


class ChatCitation(BaseModel):
    quote: str
    source: str  # marker matching the report's style, e.g. "[1]"
    section: str | None = None


class ChatResponse(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "answer": "Vendor A commits to notifying within 72 hours; Vendor B's contract states no later than 30 days [1][2].",
                    "citations": [
                        {"quote": "Vendor A will notify the customer within 72 hours of confirmation.",
                         "source": "[1]", "section": "Breach Notification"},
                        {"quote": "Vendor B shall notify ... within 30 days of becoming aware of the breach.",
                         "source": "[2]", "section": None},
                    ],
                    "grounded": True,
                    "generated_by": {"provider": "gemini", "model": "gemini-flash-latest", "usage": {}},
                }
            ]
        }
    )

    answer: str
    citations: list[ChatCitation] = Field(default_factory=list)
    grounded: bool
    generated_by: dict = Field(default_factory=dict)
