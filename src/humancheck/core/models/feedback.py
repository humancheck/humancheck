"""Feedback model - moved from models.py"""
from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, ForeignKey, Integer, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..storage.database import Base


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

