"""S3 document source."""

from __future__ import annotations

import asyncio
from datetime import timezone
from pathlib import Path

import boto3

from openlibrarian.exceptions import SourceError
from openlibrarian.sources.base import DocumentSource, FileMetadata


class S3Source(DocumentSource):
    """Document source backed by an S3 bucket."""

    def __init__(self, bucket: str, prefix: str = "", region: str = "us-east-1") -> None:
        self.bucket = bucket
        self.prefix = prefix
        try:
            self.client = boto3.client("s3", region_name=region)
        except Exception as e:
            raise SourceError(
                f"Failed to create S3 client. Ensure AWS credentials are configured "
                f"(AWS_ACCESS_KEY_ID/AWS_SECRET_ACCESS_KEY or ~/.aws/credentials): {e}"
            ) from e

    async def list_files(self) -> list[FileMetadata]:
        """List all objects in the bucket under the configured prefix."""
        return await asyncio.to_thread(self._list_files_sync)

    def _list_files_sync(self) -> list[FileMetadata]:
        files: list[FileMetadata] = []
        paginator = self.client.get_paginator("list_objects_v2")
        pages = paginator.paginate(Bucket=self.bucket, Prefix=self.prefix)
        for page in pages:
            for obj in page.get("Contents", []):
                key = obj["Key"]
                if key.endswith("/"):
                    continue
                files.append(
                    FileMetadata(
                        path=key,
                        size=obj["Size"],
                        last_modified=obj["LastModified"].replace(tzinfo=timezone.utc),
                        content_hash=obj["ETag"].strip('"'),
                    )
                )
        return files

    async def download_file(self, path: str, dest: Path) -> None:
        """Download an object from S3 to a local path."""
        dest.parent.mkdir(parents=True, exist_ok=True)
        try:
            await asyncio.to_thread(
                self.client.download_file, self.bucket, path, str(dest)
            )
        except Exception as e:
            raise SourceError(f"Failed to download s3://{self.bucket}/{path}: {e}") from e
