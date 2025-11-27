"""Decision model - moved from models.py"""
from datetime import datetime
from enum import Enum
from typing import Optional

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..storage.database import Base


class DecisionType(str, Enum):
    """Type of decision made by reviewer."""
    APPROVE = "approve"
    REJECT = "reject"
    MODIFY = "modify"


class Decision(Base):
    """Decision made on a review request."""

    __tablename__ = "decisions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    review_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("reviews.id", ondelete="CASCADE"), nullable=False, unique=True, index=True
    )
    reviewer_id: Mapped[Optional[int]] = mapped_column(
        Integer, nullable=True, index=True
    )  # Optional reviewer ID (can be used for tracking, no FK)
    reviewer_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)  # Reviewer identifier
    decision_type: Mapped[str] = mapped_column(String(50), nullable=False)
    modified_action: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    # Relationships
    review: Mapped["Review"] = relationship("Review", back_populates="decision")

    def __repr__(self) -> str:
        return f"<Decision(id={self.id}, review_id={self.review_id}, decision_type='{self.decision_type}')>"

