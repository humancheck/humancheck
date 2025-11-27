"""Feedback endpoints"""
import logging

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from ...core.models.review import Review
from ...core.models.feedback import Feedback
from ...core.schemas.feedback import FeedbackCreate, FeedbackResponse
from ..dependencies import get_session

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/reviews/{review_id}/feedback", response_model=FeedbackResponse, status_code=201)
async def submit_feedback(
    review_id: int,
    feedback_data: FeedbackCreate,
    session: AsyncSession = Depends(get_session),
):
    """Submit feedback on a review/decision."""
    try:
        # Verify review exists
        review = await session.get(Review, review_id)
        if not review:
            raise HTTPException(status_code=404, detail="Review not found")

        # Create feedback
        feedback = Feedback(
            review_id=review_id,
            rating=feedback_data.rating,
            comment=feedback_data.comment,
        )

        session.add(feedback)
        await session.commit()
        await session.refresh(feedback)

        return feedback

    except HTTPException:
        raise
    except Exception as e:
        await session.rollback()
        logger.error(f"Error submitting feedback: {e}")
        raise HTTPException(status_code=500, detail=str(e))

