"""REST API adapter for universal HTTP integration."""
import asyncio
from typing import Any, Optional

from ..models import DecisionType, ReviewStatus, UrgencyLevel
from .base import ReviewAdapter, UniversalReview


class RestAdapter(ReviewAdapter):
    """Adapter for REST API integration.

    This is the simplest adapter - it expects requests to already be in the
    UniversalReview format (or close to it) and returns simple JSON responses.
    """

    def __init__(self, db_session_factory):
        """Initialize the REST adapter.

        Args:
            db_session_factory: Factory for creating database sessions
        """
        self.db_session_factory = db_session_factory

    def to_universal(self, framework_request: dict[str, Any]) -> UniversalReview:
        """Convert REST request to UniversalReview.

        Args:
            framework_request: Dictionary with review request data

        Returns:
            UniversalReview instance
        """
        # REST requests are expected to be already in the right format
        urgency = framework_request.get("urgency", "medium")
        if isinstance(urgency, str):
            urgency = UrgencyLevel(urgency)

        return UniversalReview(
            task_type=framework_request["task_type"],
            proposed_action=framework_request["proposed_action"],
            agent_reasoning=framework_request.get("agent_reasoning"),
            confidence_score=framework_request.get("confidence_score"),
            urgency=urgency,
            framework=framework_request.get("framework", "rest"),
            metadata=framework_request.get("metadata"),
            organization_id=framework_request.get("organization_id"),
            agent_id=framework_request.get("agent_id"),
            blocking=framework_request.get("blocking", False),
        )

    def from_universal(self, universal_review: UniversalReview, decision: Any) -> dict[str, Any]:
        """Convert UniversalReview and decision to REST response.

        Args:
            universal_review: UniversalReview instance
            decision: Decision object from database

        Returns:
            Dictionary with response data
        """
        if decision is None:
            return {
                "status": "pending",
                "review": universal_review.to_dict(),
            }

        response = {
            "status": "completed",
            "decision_type": decision.decision_type,
            "review": universal_review.to_dict(),
        }

        if decision.decision_type == DecisionType.APPROVE.value:
            response["approved_action"] = universal_review.proposed_action
        elif decision.decision_type == DecisionType.REJECT.value:
            response["rejected"] = True
            response["notes"] = decision.notes
        elif decision.decision_type == DecisionType.MODIFY.value:
            response["modified_action"] = decision.modified_action

        return response

    def get_framework_name(self) -> str:
        """Get the framework name.

        Returns:
            'rest'
        """
        return "rest"

    async def handle_blocking(self, review_id: int, timeout: Optional[float] = None) -> dict[str, Any]:
        """Handle blocking review request by polling for decision.

        Args:
            review_id: ID of the review to wait for
            timeout: Optional timeout in seconds (default: 300)

        Returns:
            Decision result when available

        Raises:
            TimeoutError: If timeout is reached before decision is made
        """
        from ..models import Decision, Review

        timeout = timeout or 300.0  # 5 minutes default
        poll_interval = 1.0  # Poll every second
        elapsed = 0.0

        while elapsed < timeout:
            async with self.db_session_factory() as session:
                # Get the review
                review = await session.get(Review, review_id)
                if review is None:
                    raise ValueError(f"Review {review_id} not found")

                # Check if decision exists
                if review.status != ReviewStatus.PENDING.value:
                    decision = await session.get(Decision, review_id)
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
                    return self.from_universal(universal_review, decision)

            await asyncio.sleep(poll_interval)
            elapsed += poll_interval

        raise TimeoutError(f"Review {review_id} timed out after {timeout} seconds")
