"""Grounded chat over a report (frontend blocker #0).

Answers a question using ONLY the report's own content plus a fresh RAG retrieval
over the documents the report's job used. Reuses the existing embedding + LLM
clients. Stateless: the client replays the transcript via ``history``.
"""

from __future__ import annotations

import logging
import uuid

from sqlalchemy.orm import Session

from app.agent.llm import LLMError, get_llm_client
from app.agent.llm.embeddings import get_embedding_client
from app.core.config import settings
from app.models.job import Job
from app.models.report import Report
from app.schemas.chat import ChatMessage
from app.services import document_service

logger = logging.getLogger(__name__)


class ChatUnavailable(Exception):
    """Raised when the LLM/provider is unavailable — mapped to HTTP 503 by the route."""


_SYSTEM = (
    "You answer questions about ONE specific research report for a procurement analyst. "
    "Use ONLY the report content and the provided source passages — never outside knowledge. "
    "Cite the passages you rely on by their [n] marker. "
    "If the report and passages do not support an answer, say so plainly and set grounded=false "
    "instead of guessing. "
    "Return ONLY JSON: "
    '{"answer": str, "citations": [{"quote": str, "source": "[n]", "section": str|null}], "grounded": bool}'
)


def answer_report_question(
    db: Session, report: Report, message: str, history: list[ChatMessage]
) -> dict:
    """Produce a grounded answer + citations. Raises ChatUnavailable on LLM failure."""
    client = get_llm_client()
    if client is None:
        raise ChatUnavailable("No LLM provider is configured")

    sources = _retrieve_sources(db, report, message)
    prompt = _build_prompt(report, sources, history, message)

    try:
        resp = client.generate_json(
            _SYSTEM, prompt, temperature=settings.llm_temperature, max_tokens=settings.llm_max_tokens
        )
    except LLMError as exc:
        logger.warning("Report chat LLM call failed: %s", exc)
        raise ChatUnavailable(str(exc)) from exc

    data = resp.data if isinstance(resp.data, dict) else {}
    return {
        "answer": str(data.get("answer") or ""),
        "citations": _normalize_citations(data.get("citations")),
        "grounded": bool(data.get("grounded", False)),
        "generated_by": {"provider": client.provider, "model": client.model, "usage": resp.usage},
    }


def _retrieve_sources(db: Session, report: Report, message: str) -> list[dict]:
    """Fresh RAG retrieval over the documents the report's job used (if any)."""
    document_ids: list[uuid.UUID] = []
    if report.job_id:
        job = db.get(Job, report.job_id)
        raw = (job.input or {}).get("document_ids") if job else None
        for d in raw or []:
            try:
                document_ids.append(uuid.UUID(str(d)))
            except (ValueError, TypeError):
                continue

    embedder = get_embedding_client()
    if embedder is None or not document_ids:
        return []
    try:
        query_vector = embedder.embed([message])[0]
    except LLMError as exc:
        logger.warning("Chat retrieval embedding failed (%s); grounding on report only", exc)
        return []

    hits = document_service.search_chunks(
        db, query_vector, top_k=settings.chat_retrieval_top_k, document_ids=document_ids
    )
    return [
        {
            "index": i,
            "title": (doc.title or doc.filename) + (f" (p.{chunk.page_number})" if chunk.page_number else ""),
            "text": chunk.text,
            "document_id": str(doc.id),
            "chunk_index": chunk.chunk_index,
            "score": round(1.0 - distance, 4),
        }
        for i, (chunk, doc, distance) in enumerate(hits, start=1)
    ]


def _build_prompt(report: Report, sources: list[dict], history: list[ChatMessage], message: str) -> str:
    content = report.content or {}
    lines = [f'REPORT: "{report.title}"']
    if content.get("summary"):
        lines.append(f"Summary: {content['summary']}")
    for section in content.get("sections", []) or []:
        if isinstance(section, dict):
            lines.append(f"- {section.get('heading', 'Section')}: {section.get('body', '')}")

    lines.append("")
    if sources:
        lines.append("SOURCE PASSAGES (retrieved for this question):")
        for s in sources:
            lines.append(f"[{s['index']}] {s['title']}: {s['text']}")
    else:
        lines.append("SOURCE PASSAGES: (none — ground your answer on the report content above)")

    capped = history[-settings.chat_history_max_messages :] if history else []
    if capped:
        lines.append("")
        lines.append("CONVERSATION SO FAR:")
        for m in capped:
            who = "Assistant" if m.role == "assistant" else "User"
            lines.append(f"{who}: {m.content}")

    lines.append("")
    lines.append(f"QUESTION: {message}")
    lines.append("Answer as JSON now.")
    return "\n".join(lines)


def _normalize_citations(raw) -> list[dict]:
    out: list[dict] = []
    if not isinstance(raw, list):
        return out
    for c in raw:
        if not isinstance(c, dict):
            continue
        out.append(
            {
                "quote": str(c.get("quote") or ""),
                "source": str(c.get("source") or ""),
                "section": c.get("section") if isinstance(c.get("section"), str) else None,
            }
        )
    return out
