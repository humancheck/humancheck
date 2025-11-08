"""Core data models for reviews, decisions, and feedback."""
from datetime import datetime
from enum import Enum
from typing import Optional

from sqlalchemy import JSON, DateTime, Float, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .database import Base


class ReviewStatus(str, Enum):
    """Status of a review request."""
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    MODIFIED = "modified"


class UrgencyLevel(str, Enum):
    """Urgency level for review requests."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class DecisionType(str, Enum):
    """Type of decision made by reviewer."""
    APPROVE = "approve"
    REJECT = "reject"
    MODIFY = "modify"


class ContentCategory(str, Enum):
    """Category of attachment content."""
    TEXT = "text"
    IMAGE = "image"
    AUDIO = "audio"
    VIDEO = "video"
    DOCUMENT = "document"
    OTHER = "other"


class Review(Base):
    """Core review request model."""

    __tablename__ = "reviews"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    task_type: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    proposed_action: Mapped[str] = mapped_column(Text, nullable=False)
    agent_reasoning: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    confidence_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    urgency: Mapped[str] = mapped_column(
        String(50), nullable=False, default=UrgencyLevel.MEDIUM.value, index=True
    )
    framework: Mapped[Optional[str]] = mapped_column(String(100), nullable=True, index=True)
    status: Mapped[str] = mapped_column(
        String(50), nullable=False, default=ReviewStatus.PENDING.value, index=True
    )
    meta_data: Mapped[Optional[dict]] = mapped_column("metadata", JSON, nullable=True)

    # Multi-tenancy fields
    organization_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("organizations.id", ondelete="CASCADE"), nullable=True, index=True
    )
    agent_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("agents.id", ondelete="SET NULL"), nullable=True, index=True
    )

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    # Relationships
    decision: Mapped[Optional["Decision"]] = relationship(
        "Decision", back_populates="review", uselist=False, cascade="all, delete-orphan"
    )
    feedback: Mapped[list["Feedback"]] = relationship(
        "Feedback", back_populates="review", cascade="all, delete-orphan"
    )
    assignments: Mapped[list["ReviewAssignment"]] = relationship(
        "ReviewAssignment", back_populates="review", cascade="all, delete-orphan"
    )
    notifications: Mapped[list["NotificationLog"]] = relationship(
        "NotificationLog", back_populates="review", cascade="all, delete-orphan"
    )
    attachments: Mapped[list["Attachment"]] = relationship(
        "Attachment", back_populates="review", cascade="all, delete-orphan"
    )
    organization: Mapped[Optional["Organization"]] = relationship("Organization", back_populates="reviews")
    agent: Mapped[Optional["Agent"]] = relationship("Agent", back_populates="reviews")

    def __repr__(self) -> str:
        return f"<Review(id={self.id}, task_type='{self.task_type}', status='{self.status}')>"


class Attachment(Base):
    """File attachments for review requests."""

    __tablename__ = "attachments"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    review_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("reviews.id", ondelete="CASCADE"), nullable=False, index=True
    )

    # File metadata
    file_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    content_type: Mapped[str] = mapped_column(String(100), nullable=False)
    content_category: Mapped[str] = mapped_column(
        String(50), nullable=False, default=ContentCategory.OTHER.value, index=True
    )
    file_size: Mapped[int] = mapped_column(Integer, nullable=False)  # in bytes

    # Storage
    storage_key: Mapped[str] = mapped_column(String(500), nullable=False, unique=True)
    storage_provider: Mapped[str] = mapped_column(
        String(50), nullable=False, default="local"
    )

    # Content (for small text/inline content)
    inline_content: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Preview URLs
    preview_url: Mapped[Optional[str]] = mapped_column(String(1000), nullable=True)
    thumbnail_url: Mapped[Optional[str]] = mapped_column(String(1000), nullable=True)
    download_url: Mapped[Optional[str]] = mapped_column(String(1000), nullable=True)

    # Additional metadata
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    file_metadata: Mapped[Optional[dict]] = mapped_column("metadata", JSON, nullable=True)

    # Security
    checksum: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)  # SHA256
    virus_scan_status: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    virus_scan_result: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Timestamps
    uploaded_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    # Relationships
    review: Mapped["Review"] = relationship("Review", back_populates="attachments")

    def __repr__(self) -> str:
        return f"<Attachment(id={self.id}, file_name='{self.file_name}', content_type='{self.content_type}')>"


class Decision(Base):
    """Decision made on a review request."""

    __tablename__ = "decisions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    review_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("reviews.id", ondelete="CASCADE"), nullable=False, unique=True, index=True
    )
    reviewer_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
    )
    decision_type: Mapped[str] = mapped_column(String(50), nullable=False)
    modified_action: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    # Relationships
    review: Mapped["Review"] = relationship("Review", back_populates="decision")
    reviewer: Mapped[Optional["User"]] = relationship("User", back_populates="decisions")

    def __repr__(self) -> str:
        return f"<Decision(id={self.id}, review_id={self.review_id}, decision_type='{self.decision_type}')>"


class Feedback(Base):
    """Feedback on a review/decision."""

    __tablename__ = "feedback"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    review_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("reviews.id", ondelete="CASCADE"), nullable=False, index=True
    )
    rating: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)  # 1-5 scale
    comment: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    # Relationships
    review: Mapped["Review"] = relationship("Review", back_populates="feedback")

    def __repr__(self) -> str:
        return f"<Feedback(id={self.id}, review_id={self.review_id}, rating={self.rating})>"


class ReviewAssignment(Base):
    """Tracking of review assignments to users/teams."""

    __tablename__ = "review_assignments"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    review_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("reviews.id", ondelete="CASCADE"), nullable=False, index=True
    )
    user_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=True, index=True
    )
    team_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("teams.id", ondelete="CASCADE"), nullable=True, index=True
    )
    assigned_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    assigned_by_rule_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("routing_rules.id", ondelete="SET NULL"), nullable=True
    )

    # Relationships
    review: Mapped["Review"] = relationship("Review", back_populates="assignments")
    user: Mapped[Optional["User"]] = relationship("User", back_populates="assignments")
    team: Mapped[Optional["Team"]] = relationship("Team", back_populates="assignments")
    rule: Mapped[Optional["RoutingRule"]] = relationship("RoutingRule", back_populates="assignments")

    def __repr__(self) -> str:
        return f"<ReviewAssignment(id={self.id}, review_id={self.review_id}, user_id={self.user_id})>"


# Import to avoid circular dependency
from .connector_models import NotificationLog
from .platform_models import Agent, Organization, RoutingRule, Team, User
