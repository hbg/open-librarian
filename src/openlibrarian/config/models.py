"""Pydantic configuration models."""

from __future__ import annotations

from pathlib import Path
from typing import Literal

from pydantic import BaseModel, Field


class SourceConfig(BaseModel):
    """Document source configuration."""

    type: Literal["s3", "gcs", "local"] = "local"
    path: str | None = None  # local source directory
    bucket: str | None = None  # S3/GCS bucket name
    prefix: str = ""
    region: str = "us-east-1"


class EmbeddingsConfig(BaseModel):
    """Embedding provider configuration."""

    provider: Literal["openai", "local"] = "openai"
    model: str = "text-embedding-3-small"
    api_key: str | None = None


class ChunkingConfig(BaseModel):
    """Chunking strategy configuration."""

    strategy: Literal["semantic", "recursive"] = "semantic"
    max_tokens: int = 512
    overlap_tokens: int = 50


class ServerConfig(BaseModel):
    """MCP server configuration."""

    transport: Literal["stdio", "sse"] = "stdio"
    host: str = "127.0.0.1"
    port: int = 8080
    token: str | None = None


class IndexConfig(BaseModel):
    """Vector index storage configuration."""

    path: str = Field(default_factory=lambda: str(Path.home() / ".openlibrarian" / "index"))


class AppConfig(BaseModel):
    """Top-level application configuration."""

    source: SourceConfig = Field(default_factory=SourceConfig)
    embeddings: EmbeddingsConfig = Field(default_factory=EmbeddingsConfig)
    chunking: ChunkingConfig = Field(default_factory=ChunkingConfig)
    server: ServerConfig = Field(default_factory=ServerConfig)
    index: IndexConfig = Field(default_factory=IndexConfig)
