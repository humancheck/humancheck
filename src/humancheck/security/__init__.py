"""Backward compatibility shim for security - re-exports from core."""
from ..core.security import (
    validate_file,
    validate_content_type,
    validate_file_size,
)

__all__ = [
    "validate_file",
    "validate_content_type",
    "validate_file_size",
]
