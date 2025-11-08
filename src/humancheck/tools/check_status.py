"""MCP tool for checking review status."""
from typing import Any

from ..database import get_db
from ..models import Review


async def check_review_status(review_id: int) -> dict[str, Any]:
    """Check the status of a review request.

    Args:
        review_id: ID of the review to check

    Returns:
        Dictionary with review status and details

    Examples:
        >>> result = await check_review_status(123)
        >>> # Returns: {
        >>> #   "review_id": 123,
        >>> #   "status": "pending",
        >>> #   "task_type": "payment",
        >>> #   "created_at": "2024-01-15T10:30:00",
        >>> #   ...
        >>> # }
    """
    db = get_db()

    async with db.session() as session:
        review = await session.get(Review, review_id)

        if not review:
            return {
                "error": "Review not found",
                "review_id": review_id,
            }

        response = {
            "review_id": review.id,
            "status": review.status,
            "task_type": review.task_type,
            "proposed_action": review.proposed_action,
            "agent_reasoning": review.agent_reasoning,
            "confidence_score": review.confidence_score,
            "urgency": review.urgency,
            "framework": review.framework,
            "created_at": review.created_at.isoformat(),
            "updated_at": review.updated_at.isoformat(),
        }

        # Include metadata if present
        if review.meta_data:
            response["metadata"] = review.meta_data

        # Add status-specific information
        if review.status == "pending":
            response["message"] = "Review is still pending human decision"
        elif review.status in ["approved", "rejected", "modified"]:
            response["message"] = f"Review has been {review.status}"
            response["decision_available"] = True

        return response
