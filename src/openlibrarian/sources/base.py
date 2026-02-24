"""Abstract base class for document sources."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path


@dataclass
class FileMetadata:
    """Metadata for a file in a document source."""

    path: str
    size: int
    last_modified: datetime
    content_hash: str


class DocumentSource(ABC):
    """Abstract base for document source connectors."""

    @abstractmethod
    async def list_files(self) -> list[FileMetadata]:
        """List all files available in the source."""

    @abstractmethod
    async def download_file(self, path: str, dest: Path) -> None:
        """Download a file from the source to a local destination."""
