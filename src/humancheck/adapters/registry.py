"""Adapter registry for dynamic adapter routing."""
from typing import Optional

from .base import ReviewAdapter


class AdapterRegistry:
    """Registry for managing framework adapters.

    This allows dynamic registration and retrieval of adapters for different AI frameworks.
    """

    def __init__(self):
        """Initialize the adapter registry."""
        self._adapters: dict[str, ReviewAdapter] = {}

    def register(self, adapter: ReviewAdapter) -> None:
        """Register a new adapter.

        Args:
            adapter: ReviewAdapter instance to register

        Raises:
            ValueError: If an adapter for this framework is already registered
        """
        framework_name = adapter.get_framework_name()
        if framework_name in self._adapters:
            raise ValueError(f"Adapter for framework '{framework_name}' is already registered")
        self._adapters[framework_name] = adapter

    def get(self, framework_name: str) -> Optional[ReviewAdapter]:
        """Get an adapter by framework name.

        Args:
            framework_name: Name of the framework

        Returns:
            ReviewAdapter instance or None if not found
        """
        return self._adapters.get(framework_name)

    def unregister(self, framework_name: str) -> None:
        """Unregister an adapter.

        Args:
            framework_name: Name of the framework to unregister
        """
        if framework_name in self._adapters:
            del self._adapters[framework_name]

    def list_frameworks(self) -> list[str]:
        """Get list of registered framework names.

        Returns:
            List of framework names
        """
        return list(self._adapters.keys())

    def has_framework(self, framework_name: str) -> bool:
        """Check if a framework adapter is registered.

        Args:
            framework_name: Name of the framework

        Returns:
            True if adapter is registered, False otherwise
        """
        return framework_name in self._adapters


# Global adapter registry instance
_registry: Optional[AdapterRegistry] = None


def get_registry() -> AdapterRegistry:
    """Get the global adapter registry instance.

    Returns:
        AdapterRegistry instance
    """
    global _registry
    if _registry is None:
        _registry = AdapterRegistry()
    return _registry


def register_adapter(adapter: ReviewAdapter) -> None:
    """Register an adapter in the global registry.

    Args:
        adapter: ReviewAdapter instance to register
    """
    registry = get_registry()
    registry.register(adapter)


def get_adapter(framework_name: str) -> Optional[ReviewAdapter]:
    """Get an adapter from the global registry.

    Args:
        framework_name: Name of the framework

    Returns:
        ReviewAdapter instance or None if not found
    """
    registry = get_registry()
    return registry.get(framework_name)
