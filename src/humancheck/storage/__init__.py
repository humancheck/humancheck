"""Backward compatibility shim for storage - re-exports from core."""
from ..core.file_storage import (
    StorageProvider,
    LocalStorageProvider,
    StorageManager,
    get_storage_manager,
)

__all__ = [
    "StorageProvider",
    "LocalStorageProvider",
    "StorageManager",
    "get_storage_manager",
]
