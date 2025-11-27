"""Review endpoints"""
import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from ...core.models.review import Review, ReviewStatus, UrgencyLevel
from ...core.schemas.review import ReviewCreate, ReviewResponse, ReviewList
from ...core.routing.engine import RoutingEngine
from ...core.adapters import get_adapter
from ..dependencies import get_session

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/reviews", response_model=ReviewResponse, status_code=201)
async def create_review(
    review_data: ReviewCreate,
    session: AsyncSession = Depends(get_session),
):
    """Create a new review request.

    This endpoint accepts review requests from any framework and creates
    a review entry in the database. The review is then routed to appropriate
    reviewers based on routing rules.
    """
    try:
        # Create review
        review = Review(
            task_type=review_data.task_type,
            proposed_action=review_data.proposed_action,
            agent_reasoning=review_data.agent_reasoning,
            confidence_score=review_data.confidence_score,
            urgency=review_data.urgency.value if isinstance(review_data.urgency, UrgencyLevel) else str(review_data.urgency),
            framework=review_data.framework,
            meta_data=review_data.metadata,
            status=ReviewStatus.PENDING.value,
        )

        session.add(review)
        await session.flush()

        # Route the review
        routing_engine = RoutingEngine()
        await routing_engine.route_review(review, session)

        await session.commit()
        await session.refresh(review)

        # If blocking, wait for decision
        if review_data.blocking:
            adapter = get_adapter("rest")
            if adapter:
                try:
                    result = await adapter.handle_blocking(review.id, timeout=300.0)
                    return result
                except TimeoutError:
                    raise HTTPException(
                        status_code=408,
                        detail="Review request timed out waiting for decision"
                    )

        return review

    except HTTPException:
        raise
    except Exception as e:
        await session.rollback()
        logger.error(f"Error creating review: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/reviews", response_model=ReviewList)
async def list_reviews(
    status: Optional[str] = Query(None, description="Filter by status"),
    framework: Optional[str] = Query(None, description="Filter by framework"),
    task_type: Optional[str] = Query(None, description="Filter by task type"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    session: AsyncSession = Depends(get_session),
):
    """List reviews with optional filtering and pagination."""
    try:
        # Build query
        query = select(Review)

        if status:
            query = query.where(Review.status == status)
        if framework:
            query = query.where(Review.framework == framework)
        if task_type:
            query = query.where(Review.task_type == task_type)

        # Get total count
        count_query = select(func.count()).select_from(query.subquery())
        total_result = await session.execute(count_query)
        total = total_result.scalar_one()

        # Apply pagination
        offset = (page - 1) * page_size
        query = query.offset(offset).limit(page_size).order_by(Review.created_at.desc())

        result = await session.execute(query)
        reviews = list(result.scalars().all())

        return ReviewList(
            reviews=reviews,
            total=total,
            page=page,
            page_size=page_size,
        )

    except Exception as e:
        logger.error(f"Error listing reviews: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/reviews/{review_id}", response_model=ReviewResponse)
async def get_review(
    review_id: int,
    session: AsyncSession = Depends(get_session),
):
    """Get a specific review by ID."""
    review = await session.get(Review, review_id)
    if not review:
        raise HTTPException(status_code=404, detail="Review not found")
    return review

