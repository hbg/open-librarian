"""Tests for the LanceDB store."""

from __future__ import annotations

from pathlib import Path

from openlibrarian.pipeline.chunker import Chunk
from openlibrarian.store.lancedb import LanceStore


def _make_chunks(source: str, n: int = 3) -> tuple[list[Chunk], list[list[float]]]:
    chunks = [
        Chunk(
            chunk_id=f"{source}-{i}",
            source_path=source,
            content=f"Content {i} from {source}",
            heading=f"Heading {i}",
            chunk_index=i,
            token_estimate=10,
        )
        for i in range(n)
    ]
    vectors = [[float(i) * 0.1 + j * 0.01 for j in range(32)] for i in range(n)]
    return chunks, vectors


def test_upsert_and_list_sources(tmp_index: Path):
    store = LanceStore(str(tmp_index))
    chunks, vectors = _make_chunks("doc1.md")
    store.upsert_chunks(chunks, vectors)

    sources = store.list_sources()
    assert len(sources) == 1
    assert sources[0]["source_path"] == "doc1.md"
    assert sources[0]["chunk_count"] == 3


def test_upsert_replaces_existing(tmp_index: Path):
    store = LanceStore(str(tmp_index))

    chunks1, vectors1 = _make_chunks("doc1.md", n=3)
    store.upsert_chunks(chunks1, vectors1)

    chunks2, vectors2 = _make_chunks("doc1.md", n=2)
    store.upsert_chunks(chunks2, vectors2)

    sources = store.list_sources()
    assert sources[0]["chunk_count"] == 2


def test_search(tmp_index: Path):
    store = LanceStore(str(tmp_index))
    chunks, vectors = _make_chunks("doc1.md")
    store.upsert_chunks(chunks, vectors)

    results = store.search(vectors[0], top_k=2)
    assert len(results) <= 2
    assert results[0].source_path == "doc1.md"


def test_delete_by_source(tmp_index: Path):
    store = LanceStore(str(tmp_index))

    c1, v1 = _make_chunks("doc1.md")
    c2, v2 = _make_chunks("doc2.md")
    store.upsert_chunks(c1, v1)
    store.upsert_chunks(c2, v2)

    store.delete_by_source("doc1.md")

    sources = store.list_sources()
    paths = [s["source_path"] for s in sources]
    assert "doc1.md" not in paths
    assert "doc2.md" in paths


def test_get_chunks_by_source(tmp_index: Path):
    store = LanceStore(str(tmp_index))
    chunks, vectors = _make_chunks("doc1.md")
    store.upsert_chunks(chunks, vectors)

    result = store.get_chunks_by_source("doc1.md")
    assert len(result) == 3

    result = store.get_chunks_by_source("nonexistent.md")
    assert len(result) == 0


def test_search_empty_store(tmp_index: Path):
    store = LanceStore(str(tmp_index))
    results = store.search([0.0] * 32, top_k=5)
    assert results == []


def test_list_sources_empty(tmp_index: Path):
    store = LanceStore(str(tmp_index))
    assert store.list_sources() == []
