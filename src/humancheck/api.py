"""Backward compatibility shim for api.py - re-exports from api module."""
# Re-export the app for backward compatibility
from .api.app import app

__all__ = ["app"]
