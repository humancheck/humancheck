"""Database models for connector configuration and notification tracking."""
from datetime import datetime
from typing import Optional

from sqlalchemy import JSON, DateTime, ForeignKey, Integer, String, Text, Boolean, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .database import Base


class ConnectorConfig(Base):
    """Configuration for communication channel connectors."""

    __tablename__ = "connector_configs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    connector_type: Mapped[str] = mapped_column(
        String(50), nullable=False, index=True
    )  # 'slack', 'email', 'webhook', etc.
    name: Mapped[str] = mapped_column(String(255), nullable=False)  # Human-friendly name
    config_data: Mapped[dict] = mapped_column(JSON, nullable=False)  # API keys, endpoints, etc.
    enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, index=True)

    # Optional organization identifier (stored as metadata, no FK)
    organization_id: Mapped[Optional[int]] = mapped_column(
        Integer, nullable=True, index=True
    )

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    # Relationships
    notifications: Mapped[list["NotificationLog"]] = relationship(
        "NotificationLog", back_populates="connector", cascade="all, delete-orphan"
    )
    routing_rules: Mapped[list["ConnectorRoutingRule"]] = relationship(
        "ConnectorRoutingRule", back_populates="connector", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<ConnectorConfig(id={self.id}, type='{self.connector_type}', name='{self.name}')>"


class NotificationLog(Base):
    """Log of notifications sent through connectors."""

    __tablename__ = "notification_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    review_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("reviews.id", ondelete="CASCADE"), nullable=False, index=True
    )
    connector_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("connector_configs.id", ondelete="CASCADE"), nullable=False, index=True
    )

    # Status tracking
    status: Mapped[str] = mapped_column(
        String(50), nullable=False, index=True
    )  # 'sent', 'failed', 'delivered', 'read'
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Recipients and message tracking
    recipient: Mapped[str] = mapped_column(String(255), nullable=False)  # Channel, email, etc.
    message_id: Mapped[Optional[str]] = mapped_column(
        String(255), nullable=True, index=True
    )  # External message ID for updates

    # Timestamps
    sent_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    delivered_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    read_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    # Additional data
    notification_metadata: Mapped[Optional[dict]] = mapped_column("metadata", JSON, nullable=True)

    # Relationships
    review: Mapped["Review"] = relationship("Review", back_populates="notifications")
    connector: Mapped["ConnectorConfig"] = relationship("ConnectorConfig", back_populates="notifications")

    def __repr__(self) -> str:
        return f"<NotificationLog(id={self.id}, review_id={self.review_id}, status='{self.status}')>"


class ConnectorRoutingRule(Base):
    """Rules for routing reviews to specific connectors."""

    __tablename__ = "connector_routing_rules"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    connector_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("connector_configs.id", ondelete="CASCADE"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, index=True)
    priority: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, index=True
    )  # Higher priority rules evaluated first

    # Routing conditions (JSON with conditions to match)
    conditions: Mapped[dict] = mapped_column(JSON, nullable=False)
    # Example: {"task_type": "tool_call_execute_sql", "urgency": ["high", "critical"]}

    # Recipients for this rule
    recipients: Mapped[list] = mapped_column(JSON, nullable=False)
    # Example: ["#database-team", "@john.doe"]

    # Optional organization identifier (stored as metadata, no FK)
    organization_id: Mapped[Optional[int]] = mapped_column(
        Integer, nullable=True, index=True
    )

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    # Relationships
    connector: Mapped["ConnectorConfig"] = relationship("ConnectorConfig", back_populates="routing_rules")

    def __repr__(self) -> str:
        return f"<ConnectorRoutingRule(id={self.id}, name='{self.name}', priority={self.priority})>"


# Import to avoid circular dependency
from .models import Review
