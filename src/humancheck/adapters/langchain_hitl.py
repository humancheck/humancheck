"""LangChain HITL (Human-in-the-Loop) middleware integration for humancheck.

This adapter integrates with LangChain's HumanInTheLoopMiddleware to provide
human oversight for agent tool calls through humancheck's dashboard.
"""

import asyncio
import json
from typing import Any, Optional

from ..models import DecisionType, ReviewStatus, UrgencyLevel
from .base import ReviewAdapter, UniversalReview


class LangChainHITLAdapter(ReviewAdapter):
    """Adapter for LangChain HITL middleware integration.

    This adapter handles interrupts from LangChain's HumanInTheLoopMiddleware,
    which pauses execution when tool calls require human approval.

    The middleware provides action_requests (tool calls to review) and
    review_configs (allowed decision types per action).

    Example interrupt structure:
    {
        "action_requests": [
            {
                "name": "execute_sql",
                "arguments": {"query": "DELETE FROM records WHERE ..."},
                "description": "Tool execution pending approval..."
            }
        ],
        "review_configs": [
            {
                "action_name": "execute_sql",
                "allowed_decisions": ["approve", "reject"]
            }
        ]
    }
    """

    def __init__(self, db_session_factory, organization_id: Optional[int] = None):
        """Initialize the LangChain HITL adapter.

        Args:
            db_session_factory: Factory for creating database sessions
            organization_id: Optional organization ID for multi-tenancy
        """
        self.db_session_factory = db_session_factory
        self.organization_id = organization_id

    def to_universal(self, framework_request: dict[str, Any]) -> list[UniversalReview]:
        """Convert LangChain HITL interrupt to UniversalReview(s).

        HITL interrupts may contain multiple tool calls that need review.
        This creates one UniversalReview per tool call.

        Args:
            framework_request: Dictionary with HITL interrupt data containing:
                - action_requests: List of tool calls to review
                - review_configs: Configuration for each tool
                - thread_id: LangGraph thread ID
                - config: Additional LangGraph configuration

        Returns:
            List of UniversalReview instances (one per action_request)
        """
        action_requests = framework_request.get("action_requests", [])
        review_configs = framework_request.get("review_configs", [])
        thread_id = framework_request.get("thread_id")
        config = framework_request.get("config", {})

        # Build a map of action configs for quick lookup
        config_map = {
            cfg["action_name"]: cfg
            for cfg in review_configs
        }

        reviews = []
        for idx, action in enumerate(action_requests):
            tool_name = action.get("name", "unknown_tool")
            tool_args = action.get("arguments", {})
            description = action.get("description", "")

            # Get the review config for this action
            action_config = config_map.get(tool_name, {})
            allowed_decisions = action_config.get("allowed_decisions", ["approve", "reject", "edit"])

            # Format the proposed action to show tool call details
            proposed_action = self._format_tool_call(tool_name, tool_args)

            # Extract urgency from config or default to medium
            urgency = framework_request.get("urgency", "medium")
            if isinstance(urgency, str):
                urgency = UrgencyLevel(urgency)

            review = UniversalReview(
                task_type=f"tool_call_{tool_name}",
                proposed_action=proposed_action,
                agent_reasoning=description,
                confidence_score=framework_request.get("confidence_score"),
                urgency=urgency,
                framework="langchain_hitl",
                metadata={
                    "tool_name": tool_name,
                    "tool_arguments": tool_args,
                    "allowed_decisions": allowed_decisions,
                    "thread_id": thread_id,
                    "action_index": idx,
                    "config": config,
                    **framework_request.get("metadata", {}),
                },
                organization_id=framework_request.get("organization_id", self.organization_id),
                agent_id=framework_request.get("agent_id"),
                blocking=framework_request.get("blocking", True),
            )
            reviews.append(review)

        return reviews

    def _format_tool_call(self, tool_name: str, tool_args: dict) -> str:
        """Format a tool call for display.

        Args:
            tool_name: Name of the tool
            tool_args: Tool arguments

        Returns:
            Formatted string representation
        """
        args_str = json.dumps(tool_args, indent=2)
        return f"Tool: {tool_name}\nArguments:\n{args_str}"

    def from_universal(
        self, universal_review: UniversalReview, decision: Any
    ) -> dict[str, Any]:
        """Convert UniversalReview and decision to HITL decision format.

        HITL expects decisions in this format:
        {
            "type": "approve" | "edit" | "reject",
            "args": {...}  # Only for "edit" type
            "explanation": "..."  # Only for "reject" type
        }

        Args:
            universal_review: UniversalReview instance
            decision: Decision object from database

        Returns:
            Dictionary formatted as HITL decision
        """
        if decision is None:
            return {
                "type": "pending",
                "message": "Waiting for human review",
            }

        # Get the original tool arguments
        metadata = universal_review.metadata or {}
        tool_args = metadata.get("tool_arguments", {})

        result = {
            "timestamp": decision.timestamp.isoformat(),
            "notes": decision.notes,
        }

        if decision.decision_type == DecisionType.APPROVE.value:
            result["type"] = "approve"

        elif decision.decision_type == DecisionType.REJECT.value:
            result["type"] = "reject"
            result["explanation"] = decision.notes or "Rejected by human reviewer"

        elif decision.decision_type == DecisionType.MODIFY.value:
            # For HITL "edit", we need to parse the modified action
            # to extract the new tool arguments
            result["type"] = "edit"

            # Try to parse modified_action as JSON (tool arguments)
            try:
                modified_args = json.loads(decision.modified_action)
                result["args"] = modified_args
            except (json.JSONDecodeError, TypeError):
                # If not valid JSON, treat as full tool call text
                # and try to extract arguments
                result["args"] = self._extract_args_from_text(
                    decision.modified_action, tool_args
                )

        return result

    def _extract_args_from_text(self, text: str, fallback_args: dict) -> dict:
        """Extract tool arguments from modified action text.

        Args:
            text: Modified action text
            fallback_args: Original arguments to use if extraction fails

        Returns:
            Extracted or fallback arguments
        """
        # Try to find JSON in the text
        try:
            # Look for JSON object in the text
            start = text.find("{")
            if start != -1:
                # Find matching closing brace
                brace_count = 0
                for i in range(start, len(text)):
                    if text[i] == "{":
                        brace_count += 1
                    elif text[i] == "}":
                        brace_count -= 1
                        if brace_count == 0:
                            json_str = text[start:i+1]
                            return json.loads(json_str)
        except (json.JSONDecodeError, ValueError):
            pass

        # If extraction fails, return fallback
        return fallback_args

    def get_framework_name(self) -> str:
        """Get the framework name.

        Returns:
            'langchain_hitl'
        """
        return "langchain_hitl"

    async def handle_blocking(
        self, review_id: int, timeout: Optional[float] = None
    ) -> dict[str, Any]:
        """Handle blocking HITL request.

        Polls the database until a decision is made, then returns the
        decision in HITL format.

        Args:
            review_id: ID of the review to wait for
            timeout: Optional timeout in seconds (default: 300)

        Returns:
            HITL decision object

        Raises:
            TimeoutError: If timeout is reached before decision is made
        """
        from ..models import Decision, Review

        timeout = timeout or 300.0  # 5 minutes default for HITL
        poll_interval = 1.0  # Poll every second for responsiveness
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
            f"HITL review {review_id} timed out after {timeout} seconds"
        )


async def create_hitl_interrupt_handler(
    db_session_factory,
    organization_id: Optional[int] = None,
):
    """Create a handler function for HITL interrupts.

    This function can be used as a callback when LangChain HITL middleware
    raises an interrupt. It creates reviews in humancheck and waits for
    decisions.

    Args:
        db_session_factory: Database session factory
        organization_id: Optional organization ID

    Returns:
        Async function that handles HITL interrupts

    Example:
        ```python
        from humancheck.adapters.langchain_hitl import create_hitl_interrupt_handler
        from humancheck.database import async_session_maker

        handler = await create_hitl_interrupt_handler(async_session_maker)

        # In your LangGraph code:
        if result.get("__interrupt__"):
            decisions = await handler(result["__interrupt__"], config)
        ```
    """
    from ..api import create_review

    adapter = LangChainHITLAdapter(db_session_factory, organization_id)

    async def handle_interrupt(
        interrupt_data: list,
        config: dict
    ) -> list[dict[str, Any]]:
        """Handle a HITL interrupt by creating reviews and waiting for decisions.

        Args:
            interrupt_data: List of interrupts from LangGraph
            config: LangGraph configuration with thread_id

        Returns:
            List of decisions in HITL format
        """
        # Extract the HITL request from interrupt
        if not interrupt_data or len(interrupt_data) == 0:
            return []

        interrupt = interrupt_data[0]
        hitl_request = interrupt.value

        # Add thread_id from config
        thread_id = config.get("configurable", {}).get("thread_id")
        hitl_request["thread_id"] = thread_id
        hitl_request["config"] = config

        # Convert to UniversalReview(s)
        reviews = adapter.to_universal(hitl_request)

        # Create reviews and collect IDs
        review_ids = []
        async with db_session_factory() as session:
            for review in reviews:
                review_obj = await create_review(review, session)  # Fixed argument order
                review_ids.append(review_obj.id)
                await session.commit()

        # Wait for decisions (blocking)
        decisions = []
        for review_id in review_ids:
            decision = await adapter.handle_blocking(review_id)
            decisions.append(decision)

        return decisions

    return handle_interrupt
