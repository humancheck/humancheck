"""Backward compatibility shim for config - re-exports from core."""
from .core.config.settings import HumancheckConfig, get_config, init_config

__all__ = [
    "HumancheckConfig",
    "get_config",
    "init_config",
]
