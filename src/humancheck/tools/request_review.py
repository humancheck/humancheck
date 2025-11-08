"""MCP tool for requesting human review."""
from typing import Any, Optional

from ..adapters import McpAdapter, UniversalReview
from ..config import get_config
from ..database import get_db
from ..models import Review, ReviewStatus, UrgencyLevel
from ..routing import RoutingEngine


async def request_review(
    task_type: str,
    proposed_action: str,
    reasoning: Optional[str] = None,
    confidence: Optional[float] = None,
    urgency: str = "medium",
    blocking: bool = False,
    metadata: Optional[dict[str, Any]] = None,
    organization_id: Optional[int] = None,
    agent_id: Optional[int] = None,
) -> dict[str, Any]:
    """Request human review for an AI agent decision.

    This MCP tool allows Claude Desktop (or any MCP client) to request
    human review for uncertain or high-stakes decisions.

    Args:
        task_type: Type of task (e.g., "payment", "data_deletion", "content_moderation")
        proposed_action: The action the agent wants to take
        reasoning: Agent's reasoning for the proposed action
        confidence: Confidence score (0-1) for the proposed action
        urgency: Urgency level ("low", "medium", "high", "critical")
        blocking: Whether to block and wait for decision (default: False)
        metadata: Additional metadata as JSON
        organization_id: Organization ID for multi-tenancy
        agent_id: Agent ID

    Returns:
        Dictionary with review ID and status, or decision if blocking=True

    Examples:
        >>> # Non-blocking request
        >>> result = await request_review(
        ...     task_type="payment",
        ...     proposed_action="Process payment of $5,000 to vendor",
        ...     reasoning="Large payment requires human approval",
        ...     confidence=0.95,
        ...     urgency="high"
        ... )
        >>> # Returns: {"review_id": 123, "status": "pending", ...}

        >>> # Blocking request (waits for decision)
        >>> result = await request_review(
        ...     task_type="data_deletion",
        ...     proposed_action="Delete user account and all associated data",
        ...     reasoning="User requested GDPR data deletion",
        ...     confidence=0.99,
        ...     urgency="medium",
        ...     blocking=True
        ... )
        >>> # Returns: {"status": "completed", "decision": "approved", ...}
    """
    db = get_db()
    config = get_config()

    # Validate urgency
    valid_urgency = ["low", "medium", "high", "critical"]
    if urgency not in valid_urgency:
        raise ValueError(f"Invalid urgency. Must be one of: {valid_urgency}")

    # Validate confidence if provided
    if confidence is not None and (confidence < 0 or confidence > 1):
        raise ValueError("confidence must be between 0 and 1")

    # Create review using MCP adapter
    adapter = McpAdapter(db.session)

    request_data = {
        "task_type": task_type,
        "proposed_action": proposed_action,
        "reasoning": reasoning,
        "confidence": confidence,
        "urgency": urgency,
        "blocking": blocking,
        "metadata": metadata,
        "organization_id": organization_id,
        "agent_id": agent_id,
    }

    # Validate request
    await adapter.validate_request(request_data)

    # Convert to UniversalReview
    universal_review = adapter.to_universal(request_data)

    # Create review in database
    async with db.session() as session:
        review = Review(
            task_type=universal_review.task_type,
            proposed_action=universal_review.proposed_action,
            agent_reasoning=universal_review.agent_reasoning,
            confidence_score=universal_review.confidence_score,
            urgency=universal_review.urgency.value,
            framework=universal_review.framework,
            metadata=universal_review.metadata,
            organization_id=universal_review.organization_id,
            agent_id=universal_review.agent_id,
            status=ReviewStatus.PENDING.value,
        )

        session.add(review)
        await session.flush()

        # Route the review
        routing_engine = RoutingEngine()
        await routing_engine.route_review(review, session)

        await session.commit()

        review_id = review.id

    # If blocking, wait for decision
    if blocking:
        try:
            result = await adapter.handle_blocking(review_id, timeout=300.0)
            result["review_id"] = review_id
            return result
        except TimeoutError as e:
            return {
                "review_id": review_id,
                "status": "timeout",
                "message": str(e),
            }

    # Non-blocking response
    return {
        "review_id": review_id,
        "status": "pending",
        "message": "Review request submitted successfully. Use check_review_status to monitor progress.",
        "task_type": task_type,
        "urgency": urgency,
    }
