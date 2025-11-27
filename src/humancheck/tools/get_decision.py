"""MCP tool for getting review decision."""
from typing import Any, Optional

from ..core.adapters import McpAdapter
from ..core.storage.database import get_db
from ..core.models import Decision, Review, UrgencyLevel


async def get_review_decision(review_id: int) -> dict[str, Any]:
    """Get the decision for a review request.

    Args:
        review_id: ID of the review

    Returns:
        Dictionary with decision details if available, or error if not found

    Examples:
        >>> # Approved decision
        >>> result = await get_review_decision(123)
        >>> # Returns: {
        >>> #   "review_id": 123,
        >>> #   "status": "completed",
        >>> #   "decision": "approve",
        >>> #   "result": "approved",
        >>> #   "action": "Process payment of $5,000",
        >>> #   "message": "The proposed action has been approved.",
        >>> #   ...
        >>> # }

        >>> # Modified decision
        >>> result = await get_review_decision(124)
        >>> # Returns: {
        >>> #   "review_id": 124,
        >>> #   "status": "completed",
        >>> #   "decision": "modify",
        >>> #   "result": "modified",
        >>> #   "action": "Process payment of $3,000 instead",
        >>> #   "message": "The action was modified. ...",
        >>> #   ...
        >>> # }
    """
    db = get_db()

    async with db.session() as session:
        # Get the review
        review = await session.get(Review, review_id)
        if not review:
            return {
                "error": "Review not found",
                "review_id": review_id,
            }

        # Check if decision exists
        if review.status == "pending":
            return {
                "review_id": review_id,
                "status": "pending",
                "message": "No decision has been made yet. The review is still pending.",
            }

        # Get the decision
        decision = await session.get(Decision, review_id)
        if not decision:
            return {
                "review_id": review_id,
                "status": review.status,
                "error": "Review is marked as decided but decision not found",
            }

        # Use MCP adapter to format the response
        adapter = McpAdapter(db.session)

        from ..core.adapters import UniversalReview

        universal_review = UniversalReview(
            task_type=review.task_type,
            proposed_action=review.proposed_action,
            agent_reasoning=review.agent_reasoning,
            confidence_score=review.confidence_score,
            urgency=UrgencyLevel(review.urgency),
            framework=review.framework,
            metadata=review.meta_data,
            organization_id=review.organization_id,
            agent_id=review.agent_id,
        )

        response = adapter.from_universal(universal_review, decision)
        response["review_id"] = review_id

        return response
