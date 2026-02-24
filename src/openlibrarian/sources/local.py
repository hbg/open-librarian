"""Local filesystem document source."""

from __future__ import annotations

import hashlib
import shutil
from datetime import datetime, timezone
from pathlib import Path

from openlibrarian.exceptions import SourceError
from openlibrarian.sources.base import DocumentSource, FileMetadata


class LocalSource(DocumentSource):
    """Document source backed by a local directory."""

    def __init__(self, root: str) -> None:
        self.root = Path(root).expanduser().resolve()
        if not self.root.is_dir():
            raise SourceError(f"Source directory does not exist: {self.root}")

    async def list_files(self) -> list[FileMetadata]:
        """Walk the directory and return metadata for all files."""
        files: list[FileMetadata] = []
        for p in sorted(self.root.rglob("*")):
            if not p.is_file():
                continue
            rel = str(p.relative_to(self.root))
            stat = p.stat()
            content_hash = self._hash_file(p)
            files.append(
                FileMetadata(
                    path=rel,
                    size=stat.st_size,
                    last_modified=datetime.fromtimestamp(stat.st_mtime, tz=timezone.utc),
                    content_hash=content_hash,
                )
            )
        return files

    async def download_file(self, path: str, dest: Path) -> None:
        """Copy a file from the source directory to the destination."""
        src = self.root / path
        if not src.exists():
            raise SourceError(f"File not found in source: {src}")
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dest)

    @staticmethod
    def _hash_file(path: Path) -> str:
        """Compute MD5 hash of a file."""
        h = hashlib.md5()
        with open(path, "rb") as f:
            for chunk in iter(lambda: f.read(8192), b""):
                h.update(chunk)
        return h.hexdigest()
