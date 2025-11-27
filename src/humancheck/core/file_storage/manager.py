"""Storage manager for managing storage providers."""
from typing import Optional

from .base import StorageProvider
from .local import LocalStorageProvider


class StorageManager:
    """Manager for storage providers."""

    def __init__(self):
        """Initialize storage manager."""
        self._provider: Optional[StorageProvider] = None

    def initialize(
        self,
        provider_type: str = "local",
        **kwargs,
    ) -> None:
        """
        Initialize a storage provider.

        Args:
            provider_type: Type of storage provider ('local', 's3', 'gcs', etc.)
            **kwargs: Provider-specific configuration
        """
        if provider_type == "local":
            base_path = kwargs.get("base_path", "./storage")
            self._provider = LocalStorageProvider(base_path=base_path)
        else:
            raise ValueError(f"Unsupported storage provider: {provider_type}")

    def get(self) -> StorageProvider:
        """
        Get the initialized storage provider.

        Returns:
            StorageProvider instance

        Raises:
            RuntimeError: If provider not initialized
        """
        if self._provider is None:
            raise RuntimeError("Storage provider not initialized")
        return self._provider


# Global storage manager instance
_storage_manager = StorageManager()


def get_storage_manager() -> StorageManager:
    """Get the global storage manager instance."""
    return _storage_manager
