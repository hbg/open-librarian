"""Embedding providers for document chunks."""

from __future__ import annotations

import asyncio
from abc import ABC, abstractmethod

from openlibrarian.exceptions import EmbeddingError

BATCH_SIZE = 512


class Embedder(ABC):
    """Abstract base for embedding providers."""

    @abstractmethod
    async def embed(self, texts: list[str]) -> list[list[float]]:
        """Generate embeddings for a list of texts."""


class OpenAIEmbedder(Embedder):
    """Embedder using the OpenAI API."""

    def __init__(self, model: str = "text-embedding-3-small", api_key: str | None = None) -> None:
        try:
            import os

            from openai import OpenAI

            key = api_key or os.environ.get("OPENAI_API_KEY")
            self.client = OpenAI(api_key=key) if key else OpenAI()
        except Exception as e:
            raise EmbeddingError(
                "Failed to initialize OpenAI client. "
                f"Ensure OPENAI_API_KEY is set: {e}"
            ) from e
        self.model = model

    async def embed(self, texts: list[str]) -> list[list[float]]:
        """Embed texts in batches using the OpenAI API."""
        if not texts:
            return []

        all_embeddings: list[list[float]] = []
        for i in range(0, len(texts), BATCH_SIZE):
            batch = texts[i : i + BATCH_SIZE]
            try:
                result = await asyncio.to_thread(self._embed_batch, batch)
                all_embeddings.extend(result)
            except EmbeddingError:
                raise
            except Exception as e:
                raise EmbeddingError(f"OpenAI embedding request failed: {e}") from e
        return all_embeddings

    def _embed_batch(self, texts: list[str]) -> list[list[float]]:
        response = self.client.embeddings.create(input=texts, model=self.model)
        return [item.embedding for item in response.data]


def create_embedder(
    provider: str = "openai",
    model: str = "text-embedding-3-small",
    api_key: str | None = None,
) -> Embedder:
    """Factory to create an embedder instance."""
    if provider == "openai":
        return OpenAIEmbedder(model=model, api_key=api_key)
    raise EmbeddingError(f"Unsupported embedding provider: {provider}")
