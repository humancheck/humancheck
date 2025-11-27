"""Backward compatibility shim for connectors - re-exports from core."""
from ..core.integrations import ReviewConnector, SlackConnector

__all__ = ['ReviewConnector', 'SlackConnector']
