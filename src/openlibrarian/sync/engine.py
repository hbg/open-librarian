"""Sync engine: tracks file hashes and processes add/update/delete sets."""

from __future__ import annotations

import json
import tempfile
from pathlib import Path

from rich.console import Console

from openlibrarian.config.models import AppConfig
from openlibrarian.exceptions import SyncError
from openlibrarian.pipeline.chunker import chunk_document
from openlibrarian.pipeline.embedder import Embedder
from openlibrarian.pipeline.parser import parse_file
from openlibrarian.sources.base import DocumentSource
from openlibrarian.store.lancedb import LanceStore

console = Console()


class SyncManifest:
    """Tracks path→hash mappings for incremental sync."""

    def __init__(self, manifest_path: Path) -> None:
        self.path = manifest_path
        self.entries: dict[str, str] = {}
        if self.path.exists():
            self.entries = json.loads(self.path.read_text())

    def save(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(json.dumps(self.entries, indent=2))


class SyncEngine:
    """Orchestrates incremental sync from source to vector store."""

    def __init__(
        self,
        source: DocumentSource,
        store: LanceStore,
        embedder: Embedder,
        config: AppConfig,
    ) -> None:
        self.source = source
        self.store = store
        self.embedder = embedder
        self.config = config
        index_path = Path(config.index.path).expanduser()
        self.manifest = SyncManifest(index_path / "manifest.json")

    async def sync(self) -> dict[str, int]:
        """Run a full sync cycle. Returns counts of added, updated, deleted files."""
        try:
            remote_files = await self.source.list_files()
        except Exception as e:
            raise SyncError(f"Failed to list files from source: {e}") from e

        remote_map = {f.path: f.content_hash for f in remote_files}
        local_map = self.manifest.entries

        to_add = [p for p in remote_map if p not in local_map]
        to_update = [
            p for p in remote_map if p in local_map and remote_map[p] != local_map[p]
        ]
        to_delete = [p for p in local_map if p not in remote_map]

        counts = {"added": 0, "updated": 0, "deleted": 0, "errors": 0}

        # Process deletions
        for path in to_delete:
            console.print(f"  [red]- {path}[/red]")
            self.store.delete_by_source(path)
            del self.manifest.entries[path]
            counts["deleted"] += 1

        # Process additions and updates
        for path in to_add + to_update:
            action = "+" if path in to_add else "~"
            color = "green" if action == "+" else "yellow"
            console.print(f"  [{color}]{action} {path}[/{color}]")

            try:
                await self._process_file(path)
                self.manifest.entries[path] = remote_map[path]
                counts["added" if action == "+" else "updated"] += 1
            except Exception as e:
                console.print(f"  [red]  Error: {e}[/red]")
                counts["errors"] += 1

        self.manifest.save()
        return counts

    async def _process_file(self, path: str) -> None:
        """Download, parse, chunk, embed, and store a single file."""
        with tempfile.TemporaryDirectory() as tmp:
            local_path = Path(tmp) / Path(path).name
            await self.source.download_file(path, local_path)

            doc = parse_file(local_path, path)
            chunks = chunk_document(
                doc,
                max_tokens=self.config.chunking.max_tokens,
                overlap_tokens=self.config.chunking.overlap_tokens,
                strategy=self.config.chunking.strategy,
            )

            if not chunks:
                return

            texts = [c.content for c in chunks]
            vectors = await self.embedder.embed(texts)
            self.store.upsert_chunks(chunks, vectors)
