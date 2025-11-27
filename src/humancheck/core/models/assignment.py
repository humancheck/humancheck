"""ReviewAssignment model - moved from models.py"""
from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, ForeignKey, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..storage.database import Base


class ReviewAssignment(Base):
    """Tracking of review assignments to users/teams."""

    __tablename__ = "review_assignments"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    review_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("reviews.id", ondelete="CASCADE"), nullable=False, index=True
    )
    user_id: Mapped[Optional[int]] = mapped_column(
        Integer, nullable=True, index=True
    )  # Optional user ID (no FK, for tracking)
    reviewer_identifier: Mapped[Optional[str]] = mapped_column(
        String(255), nullable=True, index=True
    )  # Reviewer email/name identifier
    team_id: Mapped[Optional[int]] = mapped_column(
        Integer, nullable=True, index=True
    )  # Optional team ID (no FK, for tracking)
    team_name: Mapped[Optional[str]] = mapped_column(
        String(255), nullable=True
    )  # Team name identifier
    assigned_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    assigned_by_rule_id: Mapped[Optional[int]] = mapped_column(
        Integer, nullable=True
    )  # Optional rule ID (no FK)

    # Relationships
    review: Mapped["Review"] = relationship("Review", back_populates="assignments")

    def __repr__(self) -> str:
        return f"<ReviewAssignment(id={self.id}, review_id={self.review_id}, user_id={self.user_id})>"

