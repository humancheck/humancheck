"""Backward compatibility shim for routing - re-exports from core."""
from .core.routing.engine import RoutingEngine, ConditionEvaluator

__all__ = [
    "RoutingEngine",
    "ConditionEvaluator",
]
