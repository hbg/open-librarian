"""MCP server exposing search, list_sources, and get_document_context tools."""

from __future__ import annotations

from mcp.server.fastmcp import FastMCP

from openlibrarian.pipeline.embedder import Embedder, create_embedder
from openlibrarian.store.lancedb import LanceStore


def create_server(
    index_path: str,
    embedder: Embedder | None = None,
    embed_provider: str = "openai",
    embed_model: str = "text-embedding-3-small",
    embed_api_key: str | None = None,
) -> FastMCP:
    """Create and configure the MCP server.

    The server only needs the index path — no source credentials.
    An embedder is needed to convert search queries to vectors.
    """
    mcp = FastMCP("OpenLibrarian", instructions="Search and retrieve indexed documents.")
    store = LanceStore(index_path)

    # Embedder is lazily created on first search if not provided
    _embedder_ref: list[Embedder | None] = [embedder]

    def _get_embedder() -> Embedder:
        if _embedder_ref[0] is None:
            _embedder_ref[0] = create_embedder(embed_provider, embed_model, api_key=embed_api_key)
        return _embedder_ref[0]

    @mcp.tool()
    async def search(
        query: str,
        top_k: int = 5,
        source_filter: str | None = None,
    ) -> list[dict]:
        """Search indexed documents using natural language queries.

        Args:
            query: Natural language search query.
            top_k: Number of results to return (default 5).
            source_filter: Optional filter by source filename or path pattern.
        """
        embedder = _get_embedder()
        vectors = await embedder.embed([query])
        results = store.search(vectors[0], top_k=top_k, source_filter=source_filter)
        return [
            {
                "content": r.content,
                "source": r.source_path,
                "heading": r.heading,
                "score": r.score,
            }
            for r in results
        ]

    @mcp.tool()
    async def list_sources(prefix: str | None = None) -> list[dict]:
        """List all documents in the index with metadata.

        Args:
            prefix: Optional path prefix to filter by.
        """
        return store.list_sources(prefix=prefix)

    @mcp.tool()
    async def get_document_context(
        source: str,
        section: str | None = None,
        chunk_id: str | None = None,
    ) -> list[dict]:
        """Retrieve extended context from a specific document section.

        Args:
            source: Document path/filename.
            section: Optional section heading to focus on.
            chunk_id: Optional chunk ID to expand context around.
        """
        chunks = store.get_chunks_by_source(source, section=section)

        if chunk_id and chunks:
            # Find the target chunk and return surrounding context
            target_idx = next(
                (i for i, c in enumerate(chunks) if c["chunk_id"] == chunk_id),
                None,
            )
            if target_idx is not None:
                start = max(0, target_idx - 2)
                end = min(len(chunks), target_idx + 3)
                chunks = chunks[start:end]

        return chunks

    return mcp
