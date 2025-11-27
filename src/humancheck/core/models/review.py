"""Review model - moved from models.py"""
from datetime import datetime
from enum import Enum
from typing import Optional

from sqlalchemy import JSON, DateTime, Float, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..storage.database import Base


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

    # Optional metadata fields (for platform compatibility, stored in metadata)
    # organization_id and agent_id can be stored in meta_data if needed

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

    def __repr__(self) -> str:
        return f"<Review(id={self.id}, task_type='{self.task_type}', status='{self.status}')>"

