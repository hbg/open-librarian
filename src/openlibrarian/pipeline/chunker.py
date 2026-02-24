"""Chunking strategies for parsed documents."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass

from openlibrarian.pipeline.parser import ParsedDocument


@dataclass
class Chunk:
    """A chunk of document content ready for embedding."""

    chunk_id: str
    source_path: str
    content: str
    heading: str
    chunk_index: int
    token_estimate: int


def _estimate_tokens(text: str) -> int:
    """Rough token estimate: ~4 chars per token."""
    return len(text) // 4


def _make_chunk_id(source_path: str, index: int) -> str:
    """Deterministic chunk ID from source path and index."""
    raw = f"{source_path}:{index}"
    return hashlib.sha256(raw.encode()).hexdigest()[:16]


def _split_text(text: str, max_tokens: int, overlap_tokens: int) -> list[str]:
    """Split text into chunks of approximately max_tokens, with overlap."""
    max_chars = max_tokens * 4
    overlap_chars = overlap_tokens * 4

    if len(text) <= max_chars:
        return [text] if text.strip() else []

    chunks: list[str] = []
    start = 0
    while start < len(text):
        end = start + max_chars
        # Try to break at a paragraph or sentence boundary
        if end < len(text):
            # Look for a paragraph break near the end
            para_break = text.rfind("\n\n", start + max_chars // 2, end)
            if para_break > start:
                end = para_break
            else:
                # Fall back to sentence boundary
                sent_break = text.rfind(". ", start + max_chars // 2, end)
                if sent_break > start:
                    end = sent_break + 1

        chunk_text = text[start:end].strip()
        if chunk_text:
            chunks.append(chunk_text)
        start = end - overlap_chars if end < len(text) else len(text)

    return chunks


def chunk_document(
    doc: ParsedDocument,
    max_tokens: int = 512,
    overlap_tokens: int = 50,
    strategy: str = "semantic",
) -> list[Chunk]:
    """Chunk a parsed document into embedding-ready pieces.

    Semantic strategy: split on document sections first, then recursive split
    within sections if they exceed max_tokens.

    Recursive strategy: ignore sections, split the full text recursively.
    """
    chunks: list[Chunk] = []
    index = 0

    if strategy == "semantic" and doc.sections:
        for section in doc.sections:
            text = section.content
            if section.heading:
                text = f"## {section.heading}\n\n{text}"
            if not text.strip():
                continue

            if _estimate_tokens(text) <= max_tokens:
                chunks.append(
                    Chunk(
                        chunk_id=_make_chunk_id(doc.source_path, index),
                        source_path=doc.source_path,
                        content=text,
                        heading=section.heading,
                        chunk_index=index,
                        token_estimate=_estimate_tokens(text),
                    )
                )
                index += 1
            else:
                for part in _split_text(text, max_tokens, overlap_tokens):
                    chunks.append(
                        Chunk(
                            chunk_id=_make_chunk_id(doc.source_path, index),
                            source_path=doc.source_path,
                            content=part,
                            heading=section.heading,
                            chunk_index=index,
                            token_estimate=_estimate_tokens(part),
                        )
                    )
                    index += 1
    else:
        # Recursive fallback: split full text
        for part in _split_text(doc.full_text, max_tokens, overlap_tokens):
            chunks.append(
                Chunk(
                    chunk_id=_make_chunk_id(doc.source_path, index),
                    source_path=doc.source_path,
                    content=part,
                    heading="",
                    chunk_index=index,
                    token_estimate=_estimate_tokens(part),
                )
            )
            index += 1

    return chunks
