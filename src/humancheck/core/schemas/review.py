"""Review schemas - moved from schemas.py"""
from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, ConfigDict, Field

from ..models.review import ReviewStatus, UrgencyLevel


# Review schemas
class ReviewCreate(BaseModel):
    """Schema for creating a review request."""
    task_type: str = Field(..., min_length=1, max_length=255, description="Type of task")
    proposed_action: str = Field(..., min_length=1, description="The proposed action to review")
    agent_reasoning: Optional[str] = Field(None, description="Agent's reasoning for the action")
    confidence_score: Optional[float] = Field(None, ge=0.0, le=1.0, description="Confidence score (0-1)")
    urgency: UrgencyLevel = Field(default=UrgencyLevel.MEDIUM, description="Urgency level")
    framework: Optional[str] = Field(None, max_length=100, description="AI framework name")
    metadata: Optional[dict[str, Any]] = Field(None, description="Additional metadata (can include organization_id, agent_id, etc.)")
    blocking: bool = Field(default=False, description="Whether to block until decision")

    model_config = ConfigDict(use_enum_values=True)


class ReviewResponse(BaseModel):
    """Schema for review response."""
    id: int
    task_type: str
    proposed_action: str
    agent_reasoning: Optional[str]
    confidence_score: Optional[float]
    urgency: str
    framework: Optional[str]
    status: str
    metadata: Optional[dict[str, Any]] = Field(None, alias="meta_data")
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)


class ReviewList(BaseModel):
    """Schema for list of reviews with pagination."""
    reviews: list[ReviewResponse]
    total: int
    page: int
    page_size: int


# Statistics schema
class ReviewStats(BaseModel):
    """Schema for review statistics."""
    total_reviews: int
    pending_reviews: int
    approved_reviews: int
    rejected_reviews: int
    modified_reviews: int
    avg_confidence_score: Optional[float]
    task_type_breakdown: dict[str, int]
    framework_breakdown: dict[str, int]
    urgency_breakdown: dict[str, int]

