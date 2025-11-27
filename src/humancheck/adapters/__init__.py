"""Backward compatibility shim for adapters - re-exports from core."""
from ..core.adapters import (
    ReviewAdapter,
    UniversalReview,
    AdapterRegistry,
    get_registry,
    register_adapter,
    get_adapter,
    RestAdapter,
    McpAdapter,
    HumancheckLangchainAdapter,
)

__all__ = [
    "ReviewAdapter",
    "UniversalReview",
    "AdapterRegistry",
    "get_registry",
    "register_adapter",
    "get_adapter",
    "RestAdapter",
    "McpAdapter",
    "HumancheckLangchainAdapter",
]
