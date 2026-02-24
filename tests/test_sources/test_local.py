"""Tests for the local filesystem document source."""

from __future__ import annotations

from pathlib import Path

import pytest

from openlibrarian.exceptions import SourceError
from openlibrarian.sources.local import LocalSource


@pytest.mark.asyncio
async def test_list_files(sample_docs: Path):
    source = LocalSource(str(sample_docs))
    files = await source.list_files()

    paths = {f.path for f in files}
    assert "readme.md" in paths
    assert "notes.txt" in paths
    assert "sub/nested.md" in paths
    assert len(files) == 3


@pytest.mark.asyncio
async def test_list_files_has_hashes(sample_docs: Path):
    source = LocalSource(str(sample_docs))
    files = await source.list_files()
    for f in files:
        assert f.content_hash
        assert len(f.content_hash) == 32  # MD5 hex


@pytest.mark.asyncio
async def test_download_file(sample_docs: Path, tmp_dir: Path):
    source = LocalSource(str(sample_docs))
    dest = tmp_dir / "downloaded" / "readme.md"
    await source.download_file("readme.md", dest)
    assert dest.exists()
    assert "Hello" in dest.read_text()


@pytest.mark.asyncio
async def test_download_missing_file(sample_docs: Path, tmp_dir: Path):
    source = LocalSource(str(sample_docs))
    with pytest.raises(SourceError):
        await source.download_file("nonexistent.md", tmp_dir / "out.md")


def test_nonexistent_root():
    with pytest.raises(SourceError):
        LocalSource("/nonexistent/path/that/does/not/exist")
