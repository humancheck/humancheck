"""LangChain/LangGraph adapter for interrupt-based workflow integration."""
import asyncio
from typing import Any, Optional

from ..models import DecisionType, ReviewStatus, UrgencyLevel
from .base import ReviewAdapter, UniversalReview


class LangChainAdapter(ReviewAdapter):
    """Adapter for LangChain/LangGraph integration.

    LangGraph supports interrupts in state graphs. This adapter helps integrate
    with that pattern by converting interrupt data to review requests.
    """

    def __init__(self, db_session_factory):
        """Initialize the LangChain adapter.

        Args:
            db_session_factory: Factory for creating database sessions
        """
        self.db_session_factory = db_session_factory

    def to_universal(self, framework_request: dict[str, Any]) -> UniversalReview:
        """Convert LangChain request to UniversalReview.

        LangChain interrupts typically include state data and proposed next steps.

        Args:
            framework_request: Dictionary with LangChain interrupt data

        Returns:
            UniversalReview instance
        """
        # Extract task info from LangChain state
        state = framework_request.get("state", {})
        config = framework_request.get("config", {})

        urgency = framework_request.get("urgency", "medium")
        if isinstance(urgency, str):
            urgency = UrgencyLevel(urgency)

        return UniversalReview(
            task_type=framework_request.get("task_type", "langchain_interrupt"),
            proposed_action=framework_request.get("proposed_action", str(state)),
            agent_reasoning=framework_request.get("reasoning", config.get("reasoning")),
            confidence_score=framework_request.get("confidence_score"),
            urgency=urgency,
            framework="langchain",
            metadata={
                "state": state,
                "config": config,
                "interrupt_node": framework_request.get("interrupt_node"),
                **framework_request.get("metadata", {}),
            },
            organization_id=framework_request.get("organization_id"),
            agent_id=framework_request.get("agent_id"),
            blocking=framework_request.get("blocking", True),  # LangChain typically blocks
        )

    def from_universal(
        self, universal_review: UniversalReview, decision: Any
    ) -> dict[str, Any]:
        """Convert UniversalReview and decision to LangChain Command format.

        Args:
            universal_review: UniversalReview instance
            decision: Decision object from database

        Returns:
            Dictionary formatted as LangChain Command for resuming workflow
        """
        if decision is None:
            return {
                "command": "wait",
                "status": "pending",
                "message": "Waiting for human review",
            }

        # LangGraph uses Command objects to resume interrupted workflows
        result = {
            "command": "resume",
            "decision_type": decision.decision_type,
            "timestamp": decision.timestamp.isoformat(),
        }

        if decision.decision_type == DecisionType.APPROVE.value:
            result["action"] = "approved"
            result["resume_value"] = {
                "approved": True,
                "action": universal_review.proposed_action,
            }
        elif decision.decision_type == DecisionType.REJECT.value:
            result["action"] = "rejected"
            result["resume_value"] = {
                "approved": False,
                "reason": decision.notes,
            }
        elif decision.decision_type == DecisionType.MODIFY.value:
            result["action"] = "modified"
            result["resume_value"] = {
                "approved": True,
                "action": decision.modified_action,
                "modified": True,
                "original_action": universal_review.proposed_action,
            }

        return result

    def get_framework_name(self) -> str:
        """Get the framework name.

        Returns:
            'langchain'
        """
        return "langchain"

    async def handle_blocking(
        self, review_id: int, timeout: Optional[float] = None
    ) -> dict[str, Any]:
        """Handle blocking LangChain request.

        LangChain workflows typically block at interrupt points waiting for
        external input (Command objects).

        Args:
            review_id: ID of the review to wait for
            timeout: Optional timeout in seconds (default: 600 for longer workflows)

        Returns:
            Command object to resume LangChain workflow

        Raises:
            TimeoutError: If timeout is reached before decision is made
        """
        from ..models import Decision, Review

        timeout = timeout or 600.0  # 10 minutes default for LangChain
        poll_interval = 2.0
        elapsed = 0.0

        while elapsed < timeout:
            async with self.db_session_factory() as session:
                review = await session.get(Review, review_id)
                if review is None:
                    raise ValueError(f"Review {review_id} not found")

                if review.status != ReviewStatus.PENDING.value and review.decision:
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
                    return self.from_universal(universal_review, review.decision)

            await asyncio.sleep(poll_interval)
            elapsed += poll_interval

        raise TimeoutError(
            f"LangChain review {review_id} timed out after {timeout} seconds"
        )
