"""Tests for the chunker module."""

from __future__ import annotations

from openlibrarian.pipeline.chunker import Chunk, chunk_document, _split_text, _make_chunk_id
from openlibrarian.pipeline.parser import ParsedDocument, Section


def test_chunk_id_deterministic():
    id1 = _make_chunk_id("file.md", 0)
    id2 = _make_chunk_id("file.md", 0)
    id3 = _make_chunk_id("file.md", 1)
    assert id1 == id2
    assert id1 != id3


def test_split_text_short():
    """Short text should not be split."""
    result = _split_text("Hello world", max_tokens=512, overlap_tokens=50)
    assert len(result) == 1
    assert result[0] == "Hello world"


def test_split_text_long():
    """Long text should be split into multiple chunks."""
    text = "word " * 1000  # ~5000 chars => ~1250 tokens
    result = _split_text(text, max_tokens=256, overlap_tokens=25)
    assert len(result) > 1


def test_split_text_empty():
    assert _split_text("", max_tokens=512, overlap_tokens=50) == []
    assert _split_text("   ", max_tokens=512, overlap_tokens=50) == []


def test_chunk_document_semantic():
    doc = ParsedDocument(
        source_path="test.md",
        full_text="# Title\n\nIntro\n\n## Section\n\nBody",
        sections=[
            Section(heading="Title", content="Intro", level=1),
            Section(heading="Section", content="Body", level=2),
        ],
    )
    chunks = chunk_document(doc, strategy="semantic")
    assert len(chunks) == 2
    assert all(isinstance(c, Chunk) for c in chunks)
    assert chunks[0].heading == "Title"
    assert chunks[1].heading == "Section"


def test_chunk_document_recursive():
    doc = ParsedDocument(
        source_path="test.txt",
        full_text="word " * 500,
        sections=[],
    )
    chunks = chunk_document(doc, max_tokens=128, strategy="recursive")
    assert len(chunks) > 1
    assert all(c.heading == "" for c in chunks)


def test_chunk_document_semantic_falls_back_without_sections():
    doc = ParsedDocument(
        source_path="test.txt",
        full_text="Some text without sections.",
        sections=[],
    )
    chunks = chunk_document(doc, strategy="semantic")
    assert len(chunks) == 1
    assert chunks[0].content == "Some text without sections."
