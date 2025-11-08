"""MCP adapter for Claude Desktop integration."""
import asyncio
from typing import Any, Optional

from ..models import DecisionType, ReviewStatus, UrgencyLevel
from .base import ReviewAdapter, UniversalReview


class McpAdapter(ReviewAdapter):
    """Adapter for MCP (Model Context Protocol) integration.

    This adapter handles Claude Desktop's native integration format.
    """

    def __init__(self, db_session_factory):
        """Initialize the MCP adapter.

        Args:
            db_session_factory: Factory for creating database sessions
        """
        self.db_session_factory = db_session_factory

    def to_universal(self, framework_request: dict[str, Any]) -> UniversalReview:
        """Convert MCP request to UniversalReview.

        Args:
            framework_request: Dictionary with MCP-formatted request data

        Returns:
            UniversalReview instance
        """
        # MCP requests come from tool calls with specific parameter names
        urgency = framework_request.get("urgency", "medium")
        if isinstance(urgency, str):
            urgency = UrgencyLevel(urgency)

        return UniversalReview(
            task_type=framework_request["task_type"],
            proposed_action=framework_request["proposed_action"],
            agent_reasoning=framework_request.get("reasoning"),  # MCP uses 'reasoning'
            confidence_score=framework_request.get("confidence"),  # MCP uses 'confidence'
            urgency=urgency,
            framework="mcp",
            metadata=framework_request.get("metadata"),
            organization_id=framework_request.get("organization_id"),
            agent_id=framework_request.get("agent_id"),
            blocking=framework_request.get("blocking", False),
        )

    def from_universal(self, universal_review: UniversalReview, decision: Any) -> dict[str, Any]:
        """Convert UniversalReview and decision to MCP response.

        Args:
            universal_review: UniversalReview instance
            decision: Decision object from database

        Returns:
            Dictionary formatted for MCP tool response
        """
        if decision is None:
            return {
                "status": "pending",
                "message": "Review request submitted. Use check_review_status to monitor progress.",
                "task_type": universal_review.task_type,
            }

        response = {
            "status": "completed",
            "decision": decision.decision_type,
            "timestamp": decision.timestamp.isoformat(),
        }

        if decision.decision_type == DecisionType.APPROVE.value:
            response["result"] = "approved"
            response["action"] = universal_review.proposed_action
            response["message"] = "The proposed action has been approved."
        elif decision.decision_type == DecisionType.REJECT.value:
            response["result"] = "rejected"
            response["message"] = f"The proposed action was rejected. {decision.notes or ''}"
        elif decision.decision_type == DecisionType.MODIFY.value:
            response["result"] = "modified"
            response["action"] = decision.modified_action
            response["message"] = f"The action was modified. {decision.notes or ''}"

        return response

    def get_framework_name(self) -> str:
        """Get the framework name.

        Returns:
            'mcp'
        """
        return "mcp"

    async def handle_blocking(self, review_id: int, timeout: Optional[float] = None) -> dict[str, Any]:
        """Handle blocking MCP request by polling for decision.

        Args:
            review_id: ID of the review to wait for
            timeout: Optional timeout in seconds (default: 300)

        Returns:
            Decision result formatted for MCP

        Raises:
            TimeoutError: If timeout is reached before decision is made
        """
        from ..models import Decision, Review

        timeout = timeout or 300.0  # 5 minutes default
        poll_interval = 2.0  # Poll every 2 seconds for MCP
        elapsed = 0.0

        while elapsed < timeout:
            async with self.db_session_factory() as session:
                # Get the review with decision relationship
                review = await session.get(Review, review_id)
                if review is None:
                    raise ValueError(f"Review {review_id} not found")

                # Check if decision exists
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
            f"Review {review_id} timed out after {timeout} seconds. "
            "Use check_review_status to monitor the review status."
        )

    async def validate_request(self, framework_request: dict[str, Any]) -> bool:
        """Validate MCP request format.

        Args:
            framework_request: MCP-formatted request

        Returns:
            True if valid

        Raises:
            ValueError: If request is invalid
        """
        required_fields = ["task_type", "proposed_action"]
        for field in required_fields:
            if field not in framework_request:
                raise ValueError(f"Missing required field: {field}")

        # Validate urgency if provided
        if "urgency" in framework_request:
            valid_urgency = ["low", "medium", "high", "critical"]
            if framework_request["urgency"] not in valid_urgency:
                raise ValueError(f"Invalid urgency. Must be one of: {valid_urgency}")

        # Validate confidence if provided
        if "confidence" in framework_request:
            confidence = framework_request["confidence"]
            if not isinstance(confidence, (int, float)) or confidence < 0 or confidence > 1:
                raise ValueError("confidence must be a number between 0 and 1")

        return True
