"""Document source connectors."""

from __future__ import annotations

from openlibrarian.config.models import SourceConfig
from openlibrarian.exceptions import ConfigError
from openlibrarian.sources.base import DocumentSource, FileMetadata


def create_source(config: SourceConfig) -> DocumentSource:
    """Factory to create the appropriate document source."""
    if config.type == "local":
        from openlibrarian.sources.local import LocalSource

        if not config.path:
            raise ConfigError("Local source requires 'path' to be set.")
        return LocalSource(config.path)
    elif config.type == "s3":
        from openlibrarian.sources.s3 import S3Source

        if not config.bucket:
            raise ConfigError("S3 source requires 'bucket' to be set.")
        return S3Source(config.bucket, config.prefix, config.region)
    else:
        raise ConfigError(f"Unsupported source type: {config.type}")


__all__ = ["DocumentSource", "FileMetadata", "create_source"]
