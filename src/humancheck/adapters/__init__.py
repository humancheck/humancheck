"""Adapter package for framework integrations."""
from .base import ReviewAdapter, UniversalReview
from .langchain_adapter import LangChainAdapter
from .langchain_hitl import LangChainHITLAdapter, create_hitl_interrupt_handler
from .mastra_adapter import MastraAdapter
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
    "LangChainAdapter",
    "LangChainHITLAdapter",
    "create_hitl_interrupt_handler",
    "MastraAdapter",
]
