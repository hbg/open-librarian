"""LanceDB vector store implementation."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import lancedb
import pyarrow as pa

from openlibrarian.exceptions import StoreError
from openlibrarian.pipeline.chunker import Chunk

TABLE_NAME = "chunks"

SCHEMA = pa.schema(
    [
        pa.field("chunk_id", pa.string()),
        pa.field("source_path", pa.string()),
        pa.field("content", pa.string()),
        pa.field("heading", pa.string()),
        pa.field("chunk_index", pa.int32()),
        pa.field("vector", pa.list_(pa.float32())),
    ]
)


@dataclass
class SearchResult:
    """A single search result."""

    chunk_id: str
    source_path: str
    content: str
    heading: str
    chunk_index: int
    score: float


class LanceStore:
    """Vector store backed by LanceDB."""

    def __init__(self, index_path: str) -> None:
        path = Path(index_path).expanduser()
        path.mkdir(parents=True, exist_ok=True)
        try:
            self.db = lancedb.connect(str(path))
        except Exception as e:
            raise StoreError(f"Failed to open LanceDB at {path}: {e}") from e

    def _get_or_create_table(self, vector_dim: int | None = None):
        """Get existing table or create with schema if it doesn't exist."""
        try:
            return self.db.open_table(TABLE_NAME)
        except Exception:
            if vector_dim is None:
                raise StoreError(
                    "Index table does not exist yet. Run 'openlibrarian sync' first."
                )
            schema = pa.schema(
                [
                    pa.field("chunk_id", pa.string()),
                    pa.field("source_path", pa.string()),
                    pa.field("content", pa.string()),
                    pa.field("heading", pa.string()),
                    pa.field("chunk_index", pa.int32()),
                    pa.field("vector", pa.list_(pa.float32(), vector_dim)),
                ]
            )
            return self.db.create_table(TABLE_NAME, schema=schema)

    def upsert_chunks(self, chunks: list[Chunk], vectors: list[list[float]]) -> None:
        """Insert chunks with their embedding vectors. Deletes existing chunks for the same source first."""
        if not chunks:
            return

        vector_dim = len(vectors[0])
        # Delete existing chunks for this source path
        source_path = chunks[0].source_path
        self.delete_by_source(source_path, vector_dim=vector_dim)

        table = self._get_or_create_table(vector_dim)
        records = []
        for chunk, vector in zip(chunks, vectors):
            records.append(
                {
                    "chunk_id": chunk.chunk_id,
                    "source_path": chunk.source_path,
                    "content": chunk.content,
                    "heading": chunk.heading,
                    "chunk_index": chunk.chunk_index,
                    "vector": vector,
                }
            )
        try:
            table.add(records)
        except Exception as e:
            raise StoreError(f"Failed to insert chunks: {e}") from e

    def delete_by_source(self, source_path: str, vector_dim: int | None = None) -> None:
        """Delete all chunks for a given source path."""
        try:
            table = self._get_or_create_table(vector_dim)
            table.delete(f'source_path = "{source_path}"')
        except StoreError:
            pass  # Table doesn't exist yet, nothing to delete
        except Exception as e:
            raise StoreError(f"Failed to delete chunks for {source_path}: {e}") from e

    def search(
        self,
        query_vector: list[float],
        top_k: int = 5,
        source_filter: str | None = None,
    ) -> list[SearchResult]:
        """Search for similar chunks by vector similarity."""
        try:
            table = self._get_or_create_table()
        except StoreError:
            return []

        try:
            q = table.search(query_vector).limit(top_k)
            if source_filter:
                q = q.where(f'source_path LIKE "%{source_filter}%"')
            results = q.to_pandas()

            return [
                SearchResult(
                    chunk_id=row["chunk_id"],
                    source_path=row["source_path"],
                    content=row["content"],
                    heading=row["heading"],
                    chunk_index=row["chunk_index"],
                    score=float(row.get("_distance", 0.0)),
                )
                for _, row in results.iterrows()
            ]
        except Exception as e:
            raise StoreError(f"Search failed: {e}") from e

    def list_sources(self, prefix: str | None = None) -> list[dict]:
        """List all unique source documents in the index."""
        try:
            table = self._get_or_create_table()
        except StoreError:
            return []

        try:
            df = table.to_pandas()
            if df.empty:
                return []

            grouped = df.groupby("source_path").agg(
                chunk_count=("chunk_id", "count"),
            ).reset_index()

            if prefix:
                grouped = grouped[grouped["source_path"].str.startswith(prefix)]

            return [
                {"source_path": row["source_path"], "chunk_count": int(row["chunk_count"])}
                for _, row in grouped.iterrows()
            ]
        except Exception as e:
            raise StoreError(f"Failed to list sources: {e}") from e

    def get_chunks_by_source(
        self, source_path: str, section: str | None = None
    ) -> list[dict]:
        """Get all chunks for a specific source, optionally filtered by section heading."""
        try:
            table = self._get_or_create_table()
        except StoreError:
            return []

        try:
            df = table.to_pandas()
            mask = df["source_path"] == source_path
            if section:
                mask = mask & df["heading"].str.contains(section, case=False, na=False)
            filtered = df[mask].sort_values("chunk_index")

            return [
                {
                    "chunk_id": row["chunk_id"],
                    "content": row["content"],
                    "heading": row["heading"],
                    "chunk_index": int(row["chunk_index"]),
                }
                for _, row in filtered.iterrows()
            ]
        except Exception as e:
            raise StoreError(f"Failed to get chunks for {source_path}: {e}") from e
