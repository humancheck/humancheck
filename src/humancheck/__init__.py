"""Humancheck - Human-in-the-Loop Operations Platform for AI Agents.

A universal platform that enables AI agents to escalate uncertain or
high-stakes decisions to human reviewers for approval.
"""
__version__ = "0.1.2"

# Re-export from core for backward compatibility
from .core.adapters import (
    HumancheckLangchainAdapter,
    McpAdapter,
    RestAdapter,
    ReviewAdapter,
    UniversalReview,
    get_adapter,
    get_registry,
    register_adapter,
)
from .core.config.settings import HumancheckConfig, get_config, init_config
from .core.storage.database import Database, get_db, init_db
from .core.models import (
    Attachment,
    Decision,
    DecisionType,
    Feedback,
    Review,
    ReviewStatus,
    UrgencyLevel,
    ReviewAssignment,
    ContentCategory,
    ConnectorConfig,
    NotificationLog,
    ConnectorRoutingRule,
)
from .core.routing import ConditionEvaluator, RoutingEngine
from .core.schemas import (
    DecisionCreate,
    DecisionResponse,
    FeedbackCreate,
    FeedbackResponse,
    ReviewCreate,
    ReviewList,
    ReviewResponse,
    ReviewStats,
)

# Also export new core structure for platform edition
from . import core

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
    "Attachment",
    "ReviewAssignment",
    "ReviewStatus",
    "DecisionType",
    "UrgencyLevel",
    "ContentCategory",
    "ConnectorConfig",
    "NotificationLog",
    "ConnectorRoutingRule",
    # Schemas
    "ReviewCreate",
    "ReviewResponse",
    "ReviewList",
    "ReviewStats",
    "DecisionCreate",
    "DecisionResponse",
    "FeedbackCreate",
    "FeedbackResponse",
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
    # Core module
    "core",
]
