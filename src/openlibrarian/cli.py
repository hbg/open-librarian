"""CLI entrypoint for OpenLibrarian."""

from __future__ import annotations

import asyncio
from pathlib import Path

import typer
from rich.console import Console

app = typer.Typer(
    name="openlibrarian",
    help="MCP-native document retrieval service.",
    no_args_is_help=True,
)
console = Console()


@app.command()
def init(
    config_path: Path = typer.Option(
        None, "--config", "-c", help="Config file path (default: ~/.openlibrarian/config.yaml)"
    ),
) -> None:
    """Interactive setup — creates a config file."""
    from openlibrarian.config.loader import DEFAULT_CONFIG_PATH, save_config
    from openlibrarian.config.models import (
        AppConfig,
        ChunkingConfig,
        EmbeddingsConfig,
        IndexConfig,
        SourceConfig,
        ServerConfig,
    )

    dest = config_path or DEFAULT_CONFIG_PATH
    if dest.exists():
        overwrite = typer.confirm(f"Config already exists at {dest}. Overwrite?", default=False)
        if not overwrite:
            raise typer.Abort()

    console.print("\n[bold]OpenLibrarian Setup[/bold]\n")

    # Source type
    source_type = typer.prompt(
        "Document source type", default="local", type=str
    )

    source_cfg = SourceConfig(type=source_type)  # type: ignore[arg-type]
    if source_type == "local":
        source_cfg.path = typer.prompt("Path to documents directory")
    elif source_type == "s3":
        source_cfg.bucket = typer.prompt("S3 bucket name")
        source_cfg.prefix = typer.prompt("Key prefix (optional)", default="")
        source_cfg.region = typer.prompt("AWS region", default="us-east-1")
    elif source_type == "gcs":
        source_cfg.bucket = typer.prompt("GCS bucket name")
        source_cfg.prefix = typer.prompt("Key prefix (optional)", default="")

    # Embeddings
    embed_provider = typer.prompt("Embedding provider", default="openai")
    embed_model = "text-embedding-3-small"
    if embed_provider == "openai":
        embed_model = typer.prompt("Embedding model", default="text-embedding-3-small")

    config = AppConfig(
        source=source_cfg,
        embeddings=EmbeddingsConfig(provider=embed_provider, model=embed_model),  # type: ignore[arg-type]
        chunking=ChunkingConfig(),
        server=ServerConfig(),
        index=IndexConfig(),
    )

    saved_path = save_config(config, dest)
    console.print(f"\n[green]Config saved to {saved_path}[/green]")
    console.print("Next: run [bold]openlibrarian sync[/bold] to index your documents.")


@app.command()
def sync(
    config_path: Path = typer.Option(
        None, "--config", "-c", help="Config file path"
    ),
) -> None:
    """Pull, parse, chunk, embed, and index documents."""
    asyncio.run(_sync(config_path))


async def _sync(config_path: Path | None) -> None:
    from openlibrarian.config.loader import load_config
    from openlibrarian.pipeline.embedder import create_embedder
    from openlibrarian.sources import create_source
    from openlibrarian.store.lancedb import LanceStore
    from openlibrarian.sync.engine import SyncEngine

    config = load_config(config_path)
    source = create_source(config.source)
    store = LanceStore(config.index.path)
    embedder = create_embedder(config.embeddings.provider, config.embeddings.model)
    engine = SyncEngine(source, store, embedder, config)

    console.print("[bold]Syncing documents...[/bold]\n")
    counts = await engine.sync()
    console.print(
        f"\n[bold green]Done![/bold green] "
        f"Added: {counts['added']}, Updated: {counts['updated']}, "
        f"Deleted: {counts['deleted']}, Errors: {counts['errors']}"
    )


@app.command()
def serve(
    config_path: Path = typer.Option(
        None, "--config", "-c", help="Config file path"
    ),
) -> None:
    """Start the MCP server (stdio transport)."""
    from openlibrarian.config.loader import load_config
    from openlibrarian.server.mcp import create_server

    config = load_config(config_path)
    mcp = create_server(
        config.index.path,
        embed_provider=config.embeddings.provider,
        embed_model=config.embeddings.model,
        embed_api_key=config.embeddings.api_key,
    )

    Console(stderr=True).print("[bold]Starting MCP server (stdio)...[/bold]")
    mcp.run(transport="stdio")
