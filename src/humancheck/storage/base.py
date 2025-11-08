"""Base storage provider interface."""
from abc import ABC, abstractmethod
from typing import BinaryIO, Optional


class StorageProvider(ABC):
    """Abstract base class for storage providers."""

    @abstractmethod
    async def upload(
        self,
        file: BinaryIO,
        key: str,
        content_type: str,
        metadata: Optional[dict] = None,
    ) -> str:
        """
        Upload a file to storage.

        Args:
            file: File-like object to upload
            key: Unique storage key for the file
            content_type: MIME type of the file
            metadata: Optional metadata to store with file

        Returns:
            Storage key where file was saved
        """
        pass

    @abstractmethod
    async def download(self, key: str) -> bytes:
        """
        Download a file from storage.

        Args:
            key: Storage key of the file

        Returns:
            File contents as bytes
        """
        pass

    @abstractmethod
    async def delete(self, key: str) -> bool:
        """
        Delete a file from storage.

        Args:
            key: Storage key of the file

        Returns:
            True if deleted successfully
        """
        pass

    @abstractmethod
    async def exists(self, key: str) -> bool:
        """
        Check if a file exists in storage.

        Args:
            key: Storage key of the file

        Returns:
            True if file exists
        """
        pass

    @abstractmethod
    async def get_url(
        self,
        key: str,
        expires_in: int = 3600,
        download: bool = False,
    ) -> str:
        """
        Get a temporary URL for accessing the file.

        Args:
            key: Storage key of the file
            expires_in: URL expiration time in seconds
            download: If True, force download instead of inline display

        Returns:
            Temporary URL for accessing the file
        """
        pass

    @abstractmethod
    async def get_metadata(self, key: str) -> dict:
        """
        Get metadata for a stored file.

        Args:
            key: Storage key of the file

        Returns:
            Metadata dictionary
        """
        pass
