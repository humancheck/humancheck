"""Decision endpoints"""
import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from ...core.models.review import Review, ReviewStatus
from ...core.models.decision import Decision, DecisionType
from ...core.schemas.decision import DecisionCreate, DecisionResponse
from ..dependencies import get_session

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/reviews/{review_id}/decide", response_model=DecisionResponse)
async def create_decision(
    review_id: int,
    decision_data: DecisionCreate,
    session: AsyncSession = Depends(get_session),
):
    """Make a decision on a review request.

    This endpoint allows reviewers to approve, reject, or modify a review request.
    """
    try:
        # Get the review
        review = await session.get(Review, review_id)
        if not review:
            raise HTTPException(status_code=404, detail="Review not found")

        # Check if decision already exists
        existing_decision = await session.get(Decision, review_id)
        if existing_decision:
            raise HTTPException(
                status_code=409,
                detail="Decision already exists for this review"
            )

        # Create decision
        decision = Decision(
            review_id=review_id,
            reviewer_id=decision_data.reviewer_id,
            reviewer_name=decision_data.reviewer_name,
            decision_type=decision_data.decision_type.value,
            modified_action=decision_data.modified_action,
            notes=decision_data.notes,
        )

        session.add(decision)

        # Update review status
        if decision_data.decision_type == DecisionType.APPROVE:
            review.status = ReviewStatus.APPROVED.value
        elif decision_data.decision_type == DecisionType.REJECT:
            review.status = ReviewStatus.REJECTED.value
        elif decision_data.decision_type == DecisionType.MODIFY:
            review.status = ReviewStatus.MODIFIED.value

        await session.commit()
        await session.refresh(decision)

        return decision

    except HTTPException:
        raise
    except Exception as e:
        await session.rollback()
        logger.error(f"Error creating decision: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/reviews/{review_id}/decision", response_model=Optional[DecisionResponse])
async def get_decision(
    review_id: int,
    session: AsyncSession = Depends(get_session),
):
    """Get the decision for a review request."""
    decision = await session.get(Decision, review_id)
    return decision

