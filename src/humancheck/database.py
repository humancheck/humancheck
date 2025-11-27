"""Backward compatibility shim for database - re-exports from core."""
from .core.storage.database import Database, get_db, init_db, Base

__all__ = [
    "Database",
    "get_db",
    "init_db",
    "Base",
]
