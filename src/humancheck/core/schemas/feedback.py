"""Feedback schemas - moved from schemas.py"""
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


# Feedback schemas
class FeedbackCreate(BaseModel):
    """Schema for creating feedback."""
    rating: Optional[int] = Field(None, ge=1, le=5, description="Rating (1-5)")
    comment: Optional[str] = Field(None, description="Feedback comment")


class FeedbackResponse(BaseModel):
    """Schema for feedback response."""
    id: int
    review_id: int
    rating: Optional[int]
    comment: Optional[str]
    timestamp: datetime

    model_config = ConfigDict(from_attributes=True)

