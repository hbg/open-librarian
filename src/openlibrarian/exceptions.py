"""Exception hierarchy for OpenLibrarian."""


class OpenLibrarianError(Exception):
    """Base exception for all OpenLibrarian errors."""


class ConfigError(OpenLibrarianError):
    """Configuration loading or validation error."""


class SourceError(OpenLibrarianError):
    """Error accessing a document source."""


class ParseError(OpenLibrarianError):
    """Error parsing a document."""


class EmbeddingError(OpenLibrarianError):
    """Error generating embeddings."""


class StoreError(OpenLibrarianError):
    """Error reading from or writing to the vector store."""


class SyncError(OpenLibrarianError):
    """Error during document synchronization."""
