"""Backward compatibility shim for connector_manager - re-exports from core."""
from .core.integrations.manager import ConnectorManager

__all__ = [
    "ConnectorManager",
]
