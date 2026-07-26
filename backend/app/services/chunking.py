"""Split extracted document text into overlapping chunks for embedding.

Hand-rolled on purpose: chunking is simple and worth understanding. We prefer to
break on paragraph/sentence boundaries, and overlap consecutive chunks so a fact
spanning a boundary is still retrievable.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

_PARAGRAPH_SPLIT = re.compile(r"\n\s*\n")


@dataclass
class Chunk:
    index: int
    text: str
    page_number: int | None


def chunk_pages(
    pages: list[tuple[int | None, str]], *, size: int = 1000, overlap: int = 150
) -> list[Chunk]:
    """Chunk each page's text, keeping the page number for citations."""
    chunks: list[Chunk] = []
    idx = 0
    for page_number, text in pages:
        for piece in _chunk_text(text, size=size, overlap=overlap):
            chunks.append(Chunk(index=idx, text=piece, page_number=page_number))
            idx += 1
    return chunks


def _chunk_text(text: str, *, size: int, overlap: int) -> list[str]:
    clean = (text or "").strip()
    if not clean:
        return []
    if len(clean) <= size:
        return [clean]

    # Build chunks from paragraphs, flushing when adding one would exceed `size`.
    out: list[str] = []
    current = ""
    for para in _PARAGRAPH_SPLIT.split(clean):
        para = para.strip()
        if not para:
            continue
        if len(para) > size:
            if current:
                out.append(current)
                current = ""
            out.extend(_split_long(para, size=size, overlap=overlap))
            continue
        candidate = f"{current}\n\n{para}" if current else para
        if len(candidate) > size:
            out.append(current)
            current = _tail(current, overlap) + "\n\n" + para if overlap else para
        else:
            current = candidate
    if current.strip():
        out.append(current.strip())
    return [c.strip() for c in out if c.strip()]


def _split_long(text: str, *, size: int, overlap: int) -> list[str]:
    """Hard-split a very long paragraph with overlap."""
    step = max(size - overlap, 1)
    return [text[i : i + size].strip() for i in range(0, len(text), step) if text[i : i + size].strip()]


def _tail(text: str, overlap: int) -> str:
    return text[-overlap:] if overlap and len(text) > overlap else text
