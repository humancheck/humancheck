"""Mastra adapter for workflow suspend/resume integration."""
import asyncio
from typing import Any, Optional

from ..models import DecisionType, ReviewStatus, UrgencyLevel
from .base import ReviewAdapter, UniversalReview


class MastraAdapter(ReviewAdapter):
    """Adapter for Mastra workflow integration.

    Mastra supports workflow suspend/resume patterns. This adapter integrates
    with Mastra's workflow engine for human-in-the-loop decisions.
    """

    def __init__(self, db_session_factory):
        """Initialize the Mastra adapter.

        Args:
            db_session_factory: Factory for creating database sessions
        """
        self.db_session_factory = db_session_factory

    def to_universal(self, framework_request: dict[str, Any]) -> UniversalReview:
        """Convert Mastra request to UniversalReview.

        Mastra workflows include execution context and step information.

        Args:
            framework_request: Dictionary with Mastra workflow data

        Returns:
            UniversalReview instance
        """
        # Extract workflow context
        workflow_context = framework_request.get("workflow_context", {})
        step_info = framework_request.get("step_info", {})

        urgency = framework_request.get("urgency", "medium")
        if isinstance(urgency, str):
            urgency = UrgencyLevel(urgency)

        return UniversalReview(
            task_type=framework_request.get("task_type", "mastra_workflow_step"),
            proposed_action=framework_request.get("proposed_action", ""),
            agent_reasoning=framework_request.get("reasoning"),
            confidence_score=framework_request.get("confidence_score"),
            urgency=urgency,
            framework="mastra",
            metadata={
                "workflow_id": framework_request.get("workflow_id"),
                "workflow_context": workflow_context,
                "step_info": step_info,
                "execution_id": framework_request.get("execution_id"),
                **framework_request.get("metadata", {}),
            },
            organization_id=framework_request.get("organization_id"),
            agent_id=framework_request.get("agent_id"),
            blocking=framework_request.get("blocking", True),  # Mastra typically blocks
        )

    def from_universal(
        self, universal_review: UniversalReview, decision: Any
    ) -> dict[str, Any]:
        """Convert UniversalReview and decision to Mastra resume format.

        Args:
            universal_review: UniversalReview instance
            decision: Decision object from database

        Returns:
            Dictionary formatted for Mastra workflow resume
        """
        if decision is None:
            return {
                "status": "suspended",
                "message": "Workflow suspended for human review",
                "workflow_id": universal_review.metadata.get("workflow_id") if universal_review.metadata else None,
            }

        metadata = universal_review.metadata or {}
        result = {
            "status": "resuming",
            "workflow_id": metadata.get("workflow_id"),
            "execution_id": metadata.get("execution_id"),
            "decision_type": decision.decision_type,
            "timestamp": decision.timestamp.isoformat(),
        }

        if decision.decision_type == DecisionType.APPROVE.value:
            result["resume_data"] = {
                "approved": True,
                "action": universal_review.proposed_action,
                "continue_workflow": True,
            }
        elif decision.decision_type == DecisionType.REJECT.value:
            result["resume_data"] = {
                "approved": False,
                "reason": decision.notes,
                "continue_workflow": False,
            }
        elif decision.decision_type == DecisionType.MODIFY.value:
            result["resume_data"] = {
                "approved": True,
                "action": decision.modified_action,
                "modified": True,
                "original_action": universal_review.proposed_action,
                "continue_workflow": True,
            }

        return result

    def get_framework_name(self) -> str:
        """Get the framework name.

        Returns:
            'mastra'
        """
        return "mastra"

    async def handle_blocking(
        self, review_id: int, timeout: Optional[float] = None
    ) -> dict[str, Any]:
        """Handle blocking Mastra workflow request.

        Mastra workflows suspend at decision points and resume when input is provided.

        Args:
            review_id: ID of the review to wait for
            timeout: Optional timeout in seconds (default: 600)

        Returns:
            Resume data for Mastra workflow

        Raises:
            TimeoutError: If timeout is reached before decision is made
        """
        from ..models import Decision, Review

        timeout = timeout or 600.0  # 10 minutes default
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
            f"Mastra workflow review {review_id} timed out after {timeout} seconds"
        )

    async def validate_request(self, framework_request: dict[str, Any]) -> bool:
        """Validate Mastra request format.

        Args:
            framework_request: Mastra-formatted request

        Returns:
            True if valid

        Raises:
            ValueError: If request is invalid
        """
        required_fields = ["proposed_action"]
        for field in required_fields:
            if field not in framework_request:
                raise ValueError(f"Missing required field: {field}")

        # Validate workflow_id if workflow operations are expected
        if "workflow_context" in framework_request and "workflow_id" not in framework_request:
            raise ValueError("workflow_id is required when workflow_context is provided")

        return True
