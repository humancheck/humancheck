"""Humancheck - Human-in-the-Loop Operations Platform for AI Agents.

A universal platform that enables AI agents to escalate uncertain or
high-stakes decisions to human reviewers for approval.
"""
__version__ = "0.1.0"

from .adapters import (
    HumancheckLangchainAdapter,
    McpAdapter,
    RestAdapter,
    ReviewAdapter,
    UniversalReview,
    get_adapter,
    get_registry,
    register_adapter,
)
from .config import HumancheckConfig, get_config, init_config
from .database import Database, get_db, init_db
from .models import Decision, DecisionType, Feedback, Review, ReviewStatus, UrgencyLevel
from .routing import ConditionEvaluator, RoutingEngine

__all__ = [
    # Version
    "__version__",
    # Config
    "HumancheckConfig",
    "init_config",
    "get_config",
    # Database
    "Database",
    "init_db",
    "get_db",
    # Models
    "Review",
    "Decision",
    "Feedback",
    "ReviewStatus",
    "DecisionType",
    "UrgencyLevel",
    # Adapters
    "ReviewAdapter",
    "UniversalReview",
    "RestAdapter",
    "McpAdapter",
    "HumancheckLangchainAdapter",
    "get_registry",
    "register_adapter",
    "get_adapter",
    # Routing
    "RoutingEngine",
    "ConditionEvaluator",
]
