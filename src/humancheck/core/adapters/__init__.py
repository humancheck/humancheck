"""Adapter package for framework integrations."""
from .base import ReviewAdapter, UniversalReview
from .langchain import HumancheckLangchainAdapter
from .mcp_adapter import McpAdapter
from .registry import AdapterRegistry, get_adapter, get_registry, register_adapter
from .rest_adapter import RestAdapter

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
