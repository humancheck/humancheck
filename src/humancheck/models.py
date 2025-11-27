"""Backward compatibility shim for models - re-exports from core."""
# Re-export from core
from .core.models import (
    Review,
    Decision,
    Feedback,
    ReviewAssignment,
    Attachment,
    ReviewStatus,
    DecisionType,
    UrgencyLevel,
    ContentCategory,
    ConnectorConfig,
    NotificationLog,
    ConnectorRoutingRule,
)

__all__ = [
    "Review",
    "Decision",
    "Feedback",
    "ReviewAssignment",
    "Attachment",
    "ReviewStatus",
    "DecisionType",
    "UrgencyLevel",
    "ContentCategory",
    "ConnectorConfig",
    "NotificationLog",
    "ConnectorRoutingRule",
]
