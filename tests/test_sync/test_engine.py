"""Tests for the sync engine."""

from __future__ import annotations

from pathlib import Path

import pytest

from openlibrarian.config.models import AppConfig, IndexConfig, SourceConfig, ChunkingConfig
from openlibrarian.sources.local import LocalSource
from openlibrarian.store.lancedb import LanceStore
from openlibrarian.sync.engine import SyncEngine, SyncManifest


@pytest.mark.asyncio
async def test_sync_adds_new_files(sample_docs: Path, tmp_index: Path, mock_embedder):
    config = AppConfig(
        source=SourceConfig(type="local", path=str(sample_docs)),
        index=IndexConfig(path=str(tmp_index)),
        chunking=ChunkingConfig(strategy="recursive"),
    )
    source = LocalSource(str(sample_docs))
    store = LanceStore(str(tmp_index))
    engine = SyncEngine(source, store, mock_embedder, config)

    counts = await engine.sync()
    assert counts["added"] == 3
    assert counts["updated"] == 0
    assert counts["deleted"] == 0

    sources = store.list_sources()
    assert len(sources) == 3


@pytest.mark.asyncio
async def test_sync_incremental(sample_docs: Path, tmp_index: Path, mock_embedder):
    config = AppConfig(
        source=SourceConfig(type="local", path=str(sample_docs)),
        index=IndexConfig(path=str(tmp_index)),
        chunking=ChunkingConfig(strategy="recursive"),
    )
    source = LocalSource(str(sample_docs))
    store = LanceStore(str(tmp_index))
    engine = SyncEngine(source, store, mock_embedder, config)

    # First sync
    await engine.sync()

    # Second sync — no changes
    counts = await engine.sync()
    assert counts["added"] == 0
    assert counts["updated"] == 0
    assert counts["deleted"] == 0


@pytest.mark.asyncio
async def test_sync_detects_changes(sample_docs: Path, tmp_index: Path, mock_embedder):
    config = AppConfig(
        source=SourceConfig(type="local", path=str(sample_docs)),
        index=IndexConfig(path=str(tmp_index)),
        chunking=ChunkingConfig(strategy="recursive"),
    )
    source = LocalSource(str(sample_docs))
    store = LanceStore(str(tmp_index))
    engine = SyncEngine(source, store, mock_embedder, config)

    await engine.sync()

    # Modify a file
    (sample_docs / "readme.md").write_text("# Updated\n\nNew content.\n")

    counts = await engine.sync()
    assert counts["updated"] == 1


@pytest.mark.asyncio
async def test_sync_detects_deletions(sample_docs: Path, tmp_index: Path, mock_embedder):
    config = AppConfig(
        source=SourceConfig(type="local", path=str(sample_docs)),
        index=IndexConfig(path=str(tmp_index)),
        chunking=ChunkingConfig(strategy="recursive"),
    )
    source = LocalSource(str(sample_docs))
    store = LanceStore(str(tmp_index))
    engine = SyncEngine(source, store, mock_embedder, config)

    await engine.sync()

    # Delete a file
    (sample_docs / "notes.txt").unlink()

    counts = await engine.sync()
    assert counts["deleted"] == 1


def test_manifest_persistence(tmp_index: Path):
    manifest_path = tmp_index / "manifest.json"

    m1 = SyncManifest(manifest_path)
    m1.entries["file.md"] = "abc123"
    m1.save()

    m2 = SyncManifest(manifest_path)
    assert m2.entries["file.md"] == "abc123"
