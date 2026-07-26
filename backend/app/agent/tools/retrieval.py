"""Retrieval tool (RAG's "R") — find the passages most relevant to the query.

Embeds the query and runs a pgvector cosine search over ingested document chunks.
Falls back to inline ``input.sources`` (Milestone 6 step 2 behaviour) when no
documents are available, so older-style jobs keep working.
"""

from __future__ import annotations

import logging
import uuid

from app.agent.base import Tool, ToolContext, ToolResult
from app.agent.llm.base import LLMError
from app.agent.llm.embeddings import get_embedding_client
from app.core.config import settings
from app.db.session import SessionLocal
from app.services import document_service

logger = logging.getLogger(__name__)


class RetrievalTool(Tool):
    key = "retrieval"
    name = "Retrieving relevant passages"
    required = True

    def run(self, ctx: ToolContext) -> ToolResult:
        if self._forced_failure(ctx):
            return ToolResult.failed("forced retrieval failure")

        query = ctx.input.get("query") or ""
        raw_ids = ctx.input.get("document_ids") or []
        top_k = int(ctx.input.get("top_k") or settings.retrieval_top_k)

        try:
            document_ids = [uuid.UUID(str(d)) for d in raw_ids]
        except (ValueError, TypeError) as exc:
            return ToolResult.failed(f"invalid document_ids: {exc}")

        client = get_embedding_client()
        if client is None or not query:
            return self._inline_fallback(ctx, "no embedding provider configured" if not client else "empty query")

        try:
            query_vector = client.embed([query])[0]
        except LLMError as exc:
            logger.warning("Query embedding failed (%s); using inline sources", exc)
            return self._inline_fallback(ctx, f"embedding error: {exc}")

        with SessionLocal() as db:
            hits = document_service.search_chunks(
                db, query_vector, top_k=top_k, document_ids=document_ids or None
            )
            sources = [
                {
                    "title": f"{doc.title or doc.filename}"
                    + (f" (p.{chunk.page_number})" if chunk.page_number else ""),
                    "text": chunk.text,
                    "document_id": str(doc.id),
                    "chunk_index": chunk.chunk_index,
                    "score": round(1.0 - distance, 4),  # cosine similarity
                }
                for chunk, doc, distance in hits
            ]

        if not sources:
            return self._inline_fallback(ctx, "no matching chunks found")

        ctx.artifacts["sources"] = sources
        ctx.input["sources"] = sources  # synthesis reads sources from input
        return ToolResult.ok(
            {
                "retrieved": len(sources),
                "top_k": top_k,
                "documents_searched": len(document_ids) or "all",
                "top_score": sources[0]["score"],
            }
        )

    @staticmethod
    def _inline_fallback(ctx: ToolContext, reason: str) -> ToolResult:
        """Use sources passed directly in the job input (pre-RAG behaviour)."""
        inline = ctx.input.get("sources") or []
        ctx.artifacts["sources"] = inline
        return ToolResult.ok({"retrieved": len(inline), "mode": "inline", "reason": reason})
