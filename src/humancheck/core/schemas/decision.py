"""Decision schemas - moved from schemas.py"""
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator

from ..models.decision import DecisionType


# Decision schemas
class DecisionCreate(BaseModel):
    """Schema for creating a decision."""
    decision_type: DecisionType = Field(..., description="Type of decision")
    modified_action: Optional[str] = Field(None, description="Modified action if decision is MODIFY")
    notes: Optional[str] = Field(None, description="Additional notes")
    reviewer_id: Optional[int] = Field(None, description="Optional reviewer ID (for tracking)")
    reviewer_name: Optional[str] = Field(None, description="Reviewer name/email identifier")

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
    reviewer_name: Optional[str]
    decision_type: str
    modified_action: Optional[str]
    notes: Optional[str]
    timestamp: datetime

    model_config = ConfigDict(from_attributes=True)

