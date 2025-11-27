"""Statistics endpoints"""
import logging
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from fastapi import APIRouter, Depends, HTTPException

from ...core.models.review import Review, ReviewStatus
from ...core.schemas.review import ReviewStats
from ..dependencies import get_session

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/stats", response_model=ReviewStats)
async def get_statistics(
    session: AsyncSession = Depends(get_session),
):
    """Get review statistics and analytics."""
    try:
        # Build base query
        query = select(Review)

        result = await session.execute(query)
        reviews = list(result.scalars().all())

        # Calculate statistics
        total_reviews = len(reviews)
        pending_reviews = sum(1 for r in reviews if r.status == ReviewStatus.PENDING.value)
        approved_reviews = sum(1 for r in reviews if r.status == ReviewStatus.APPROVED.value)
        rejected_reviews = sum(1 for r in reviews if r.status == ReviewStatus.REJECTED.value)
        modified_reviews = sum(1 for r in reviews if r.status == ReviewStatus.MODIFIED.value)

        # Average confidence score
        confidence_scores = [r.confidence_score for r in reviews if r.confidence_score is not None]
        avg_confidence = sum(confidence_scores) / len(confidence_scores) if confidence_scores else None

        # Task type breakdown
        task_type_breakdown = {}
        for review in reviews:
            task_type_breakdown[review.task_type] = task_type_breakdown.get(review.task_type, 0) + 1

        # Framework breakdown
        framework_breakdown = {}
        for review in reviews:
            if review.framework:
                framework_breakdown[review.framework] = framework_breakdown.get(review.framework, 0) + 1

        # Urgency breakdown
        urgency_breakdown = {}
        for review in reviews:
            urgency_breakdown[review.urgency] = urgency_breakdown.get(review.urgency, 0) + 1

        return ReviewStats(
            total_reviews=total_reviews,
            pending_reviews=pending_reviews,
            approved_reviews=approved_reviews,
            rejected_reviews=rejected_reviews,
            modified_reviews=modified_reviews,
            avg_confidence_score=avg_confidence,
            task_type_breakdown=task_type_breakdown,
            framework_breakdown=framework_breakdown,
            urgency_breakdown=urgency_breakdown,
        )

    except Exception as e:
        logger.error(f"Error getting statistics: {e}")
        raise HTTPException(status_code=500, detail=str(e))

