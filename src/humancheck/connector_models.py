"""Backward compatibility shim for connector_models - re-exports from core."""
from .core.models.connector import (
    ConnectorConfig,
    NotificationLog,
    ConnectorRoutingRule,
)

__all__ = [
    "ConnectorConfig",
    "NotificationLog",
    "ConnectorRoutingRule",
]
