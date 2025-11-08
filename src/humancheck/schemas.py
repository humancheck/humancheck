"""Pydantic schemas for API validation and serialization."""
from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator

from .models import DecisionType, ReviewStatus, UrgencyLevel


# Review schemas
class ReviewCreate(BaseModel):
    """Schema for creating a review request."""
    task_type: str = Field(..., min_length=1, max_length=255, description="Type of task")
    proposed_action: str = Field(..., min_length=1, description="The proposed action to review")
    agent_reasoning: Optional[str] = Field(None, description="Agent's reasoning for the action")
    confidence_score: Optional[float] = Field(None, ge=0.0, le=1.0, description="Confidence score (0-1)")
    urgency: UrgencyLevel = Field(default=UrgencyLevel.MEDIUM, description="Urgency level")
    framework: Optional[str] = Field(None, max_length=100, description="AI framework name")
    metadata: Optional[dict[str, Any]] = Field(None, description="Additional metadata")
    organization_id: Optional[int] = Field(None, description="Organization ID for multi-tenancy")
    agent_id: Optional[int] = Field(None, description="Agent ID")
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
    organization_id: Optional[int]
    agent_id: Optional[int]
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)


class ReviewList(BaseModel):
    """Schema for list of reviews with pagination."""
    reviews: list[ReviewResponse]
    total: int
    page: int
    page_size: int


# Decision schemas
class DecisionCreate(BaseModel):
    """Schema for creating a decision."""
    decision_type: DecisionType = Field(..., description="Type of decision")
    modified_action: Optional[str] = Field(None, description="Modified action if decision is MODIFY")
    notes: Optional[str] = Field(None, description="Additional notes")
    reviewer_id: Optional[int] = Field(None, description="ID of the reviewer")

    @field_validator("modified_action")
    @classmethod
    def validate_modified_action(cls, v: Optional[str], info) -> Optional[str]:
        """Ensure modified_action is provided when decision_type is MODIFY."""
        if info.data.get("decision_type") == DecisionType.MODIFY and not v:
            raise ValueError("modified_action is required when decision_type is MODIFY")
        return v

    model_config = ConfigDict(use_enum_values=True)


class DecisionResponse(BaseModel):
    """Schema for decision response."""
    id: int
    review_id: int
    reviewer_id: Optional[int]
    decision_type: str
    modified_action: Optional[str]
    notes: Optional[str]
    timestamp: datetime

    model_config = ConfigDict(from_attributes=True)


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


# Organization schemas
class OrganizationCreate(BaseModel):
    """Schema for creating an organization."""
    name: str = Field(..., min_length=1, max_length=255)
    settings: Optional[dict[str, Any]] = None


class OrganizationResponse(BaseModel):
    """Schema for organization response."""
    id: int
    name: str
    settings: Optional[dict[str, Any]]
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


# User schemas
class UserCreate(BaseModel):
    """Schema for creating a user."""
    email: str = Field(..., max_length=255)
    name: str = Field(..., min_length=1, max_length=255)
    role: str = Field(default="reviewer", pattern="^(admin|reviewer|viewer)$")
    organization_id: int


class UserResponse(BaseModel):
    """Schema for user response."""
    id: int
    email: str
    name: str
    role: str
    organization_id: int
    is_active: bool
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


# Team schemas
class TeamCreate(BaseModel):
    """Schema for creating a team."""
    name: str = Field(..., min_length=1, max_length=255)
    organization_id: int
    settings: Optional[dict[str, Any]] = None


class TeamResponse(BaseModel):
    """Schema for team response."""
    id: int
    name: str
    organization_id: int
    settings: Optional[dict[str, Any]]
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


# Agent schemas
class AgentCreate(BaseModel):
    """Schema for creating an agent."""
    name: str = Field(..., min_length=1, max_length=255)
    framework: str = Field(..., min_length=1, max_length=100)
    organization_id: int
    description: Optional[str] = None
    metadata: Optional[dict[str, Any]] = None


class AgentResponse(BaseModel):
    """Schema for agent response."""
    id: int
    name: str
    framework: str
    organization_id: int
    description: Optional[str]
    metadata: Optional[dict[str, Any]] = Field(None, alias="meta_data")
    created_at: datetime

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)


# Routing Rule schemas
class RoutingRuleCreate(BaseModel):
    """Schema for creating a routing rule."""
    name: str = Field(..., min_length=1, max_length=255)
    organization_id: int
    priority: int = Field(default=0, description="Higher priority rules are evaluated first")
    conditions: dict[str, Any] = Field(..., description="Condition rules in JSON format")
    assign_to_user_id: Optional[int] = None
    assign_to_team_id: Optional[int] = None
    is_active: bool = True

    @field_validator("conditions")
    @classmethod
    def validate_conditions(cls, v: dict[str, Any]) -> dict[str, Any]:
        """Validate that conditions is a non-empty dict."""
        if not v:
            raise ValueError("conditions must be a non-empty dictionary")
        return v


class RoutingRuleResponse(BaseModel):
    """Schema for routing rule response."""
    id: int
    name: str
    organization_id: int
    priority: int
    conditions: dict[str, Any]
    assign_to_user_id: Optional[int]
    assign_to_team_id: Optional[int]
    is_active: bool
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


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
