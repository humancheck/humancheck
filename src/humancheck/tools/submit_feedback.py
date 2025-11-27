"""MCP tool for submitting feedback on reviews."""
from typing import Any, Optional

from ..core.storage.database import get_db
from ..core.models import Feedback, Review


async def submit_feedback(
    review_id: int,
    rating: Optional[int] = None,
    comment: Optional[str] = None,
) -> dict[str, Any]:
    """Submit feedback on a review/decision.

    This allows agents to provide feedback on the review process and decisions,
    enabling continuous improvement of the human-in-the-loop system.

    Args:
        review_id: ID of the review to provide feedback for
        rating: Rating from 1-5 (optional)
        comment: Feedback comment (optional)

    Returns:
        Dictionary with feedback confirmation

    Examples:
        >>> # Submit rating and comment
        >>> result = await submit_feedback(
        ...     review_id=123,
        ...     rating=5,
        ...     comment="Quick and helpful review, thank you!"
        ... )
        >>> # Returns: {
        >>> #   "success": True,
        >>> #   "review_id": 123,
        >>> #   "message": "Feedback submitted successfully",
        >>> #   ...
        >>> # }

        >>> # Submit just a comment
        >>> result = await submit_feedback(
        ...     review_id=124,
        ...     comment="The modified action worked perfectly"
        ... )
    """
    # Validate rating if provided
    if rating is not None and (rating < 1 or rating > 5):
        return {
            "success": False,
            "error": "Rating must be between 1 and 5",
        }

    # At least one of rating or comment should be provided
    if rating is None and not comment:
        return {
            "success": False,
            "error": "Please provide either a rating or comment",
        }

    db = get_db()

    async with db.session() as session:
        # Verify review exists
        review = await session.get(Review, review_id)
        if not review:
            return {
                "success": False,
                "error": "Review not found",
                "review_id": review_id,
            }

        # Create feedback
        feedback = Feedback(
            review_id=review_id,
            rating=rating,
            comment=comment,
        )

        session.add(feedback)
        await session.commit()

        return {
            "success": True,
            "review_id": review_id,
            "message": "Feedback submitted successfully. Thank you for helping improve the review process!",
            "rating": rating,
            "has_comment": bool(comment),
        }
