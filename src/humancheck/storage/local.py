"""Local filesystem storage provider."""
import json
import os
from pathlib import Path
from typing import BinaryIO, Optional
from urllib.parse import quote

from .base import StorageProvider


class LocalStorageProvider(StorageProvider):
    """Storage provider using local filesystem."""

    def __init__(self, base_path: str = "./storage"):
        """
        Initialize local storage provider.

        Args:
            base_path: Base directory for storing files
        """
        self.base_path = Path(base_path)
        self.base_path.mkdir(parents=True, exist_ok=True)

    def _get_file_path(self, key: str) -> Path:
        """Get full file path for a storage key."""
        # Sanitize the key to prevent directory traversal
        safe_key = key.replace("..", "").lstrip("/")
        return self.base_path / safe_key

    def _get_metadata_path(self, key: str) -> Path:
        """Get metadata file path for a storage key."""
        return self._get_file_path(f"{key}.meta")

    async def upload(
        self,
        file: BinaryIO,
        key: str,
        content_type: str,
        metadata: Optional[dict] = None,
    ) -> str:
        """Upload a file to local storage."""
        file_path = self._get_file_path(key)

        # Create parent directories
        file_path.parent.mkdir(parents=True, exist_ok=True)

        # Write file
        with open(file_path, "wb") as f:
            content = file.read()
            f.write(content)

        # Write metadata
        meta = {
            "content_type": content_type,
            "size": len(content),
            **(metadata or {}),
        }

        meta_path = self._get_metadata_path(key)
        with open(meta_path, "w") as f:
            json.dump(meta, f)

        return key

    async def download(self, key: str) -> bytes:
        """Download a file from local storage."""
        file_path = self._get_file_path(key)

        if not file_path.exists():
            raise FileNotFoundError(f"File not found: {key}")

        with open(file_path, "rb") as f:
            return f.read()

    async def delete(self, key: str) -> bool:
        """Delete a file from local storage."""
        file_path = self._get_file_path(key)
        meta_path = self._get_metadata_path(key)

        deleted = False

        if file_path.exists():
            file_path.unlink()
            deleted = True

        if meta_path.exists():
            meta_path.unlink()

        return deleted

    async def exists(self, key: str) -> bool:
        """Check if a file exists in local storage."""
        file_path = self._get_file_path(key)
        return file_path.exists()

    async def get_url(
        self,
        key: str,
        expires_in: int = 3600,
        download: bool = False,
    ) -> str:
        """
        Get a URL for accessing the file.

        Note: For local storage, this returns a relative path.
        In production, you'd use signed URLs with a web server.
        """
        # URL encode the key
        encoded_key = quote(key)

        # In a real implementation, this would generate a signed URL
        # For now, return a simple API path
        disposition = "attachment" if download else "inline"
        return f"/api/attachments/download/{encoded_key}?disposition={disposition}"

    async def get_metadata(self, key: str) -> dict:
        """Get metadata for a stored file."""
        meta_path = self._get_metadata_path(key)

        if not meta_path.exists():
            return {}

        with open(meta_path, "r") as f:
            return json.load(f)
