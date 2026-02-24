"""Shared test fixtures."""

from __future__ import annotations

import tempfile
from pathlib import Path

import pytest

from openlibrarian.pipeline.embedder import Embedder


class MockEmbedder(Embedder):
    """Deterministic embedder for tests — returns fixed-dimension vectors."""

    def __init__(self, dim: int = 32) -> None:
        self.dim = dim

    async def embed(self, texts: list[str]) -> list[list[float]]:
        vectors = []
        for text in texts:
            # Deterministic: hash text to produce a stable vector
            val = hash(text) % 1000 / 1000.0
            vectors.append([val + (i * 0.001) for i in range(self.dim)])
        return vectors


@pytest.fixture
def tmp_dir():
    """Provide a temporary directory that's cleaned up after the test."""
    with tempfile.TemporaryDirectory() as d:
        yield Path(d)


@pytest.fixture
def sample_docs(tmp_dir: Path) -> Path:
    """Create a directory with sample documents for testing."""
    docs = tmp_dir / "docs"
    docs.mkdir()

    (docs / "readme.md").write_text("# Hello\n\nThis is a test document.\n\n## Section 1\n\nSome content here.\n\n## Section 2\n\nMore content here.\n")
    (docs / "notes.txt").write_text("These are plain text notes.\nLine two.\nLine three.\n")
    (docs / "sub").mkdir()
    (docs / "sub" / "nested.md").write_text("# Nested\n\nA nested document.\n")

    return docs


@pytest.fixture
def mock_embedder() -> MockEmbedder:
    return MockEmbedder(dim=32)


@pytest.fixture
def tmp_index(tmp_dir: Path) -> Path:
    """Provide a temporary directory for the LanceDB index."""
    index = tmp_dir / "index"
    index.mkdir()
    return index
