"""Routing engine for intelligent review assignment."""
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session

from ..config.settings import get_config
from ..models import Review, ReviewAssignment
from .evaluator import ConditionEvaluator


class RoutingEngine:
    """Engine for routing reviews to appropriate reviewers based on config.

    The routing engine uses configuration-based routing rules to assign reviews
    to reviewers based on matching conditions.
    """

    def __init__(self):
        """Initialize the routing engine."""
        self.evaluator = ConditionEvaluator()
        self.config = get_config()

    async def route_review(
        self, review: Review, session: Session | AsyncSession
    ) -> list[ReviewAssignment]:
        """Route a review to appropriate reviewers.

        Args:
            review: Review to route
            session: Database session

        Returns:
            List of ReviewAssignment objects created
        """
        # Get routing rules from config
        routing_rules = self.config.model_dump().get("routing_rules", [])

        # Prepare review data for evaluation
        review_data = {
            "task_type": review.task_type,
            "confidence_score": review.confidence_score,
            "urgency": review.urgency,
            "framework": review.framework,
            "metadata": review.meta_data or {},
        }

        assignments = []

        # Evaluate rules in priority order (if configured)
        for rule in routing_rules:
            if not rule.get("is_active", True):
                continue

            # Check if conditions match
            conditions = rule.get("conditions", {})
            if self.evaluator.evaluate(conditions, review_data):
                # Create assignment based on rule
                reviewer_identifier = rule.get("assign_to")
                team_name = rule.get("assign_to_team")

                if reviewer_identifier or team_name:
                    assignment = ReviewAssignment(
                        review_id=review.id,
                        reviewer_identifier=reviewer_identifier,
                        team_name=team_name,
                    )
                    session.add(assignment)
                    if isinstance(session, AsyncSession):
                        await session.flush()
                    else:
                        session.flush()
                    assignments.append(assignment)
                    break  # Stop after first match

        # If no rules matched, use default assignment
        if not assignments:
            default_assignment = await self._create_default_assignment(review, session)
            if default_assignment:
                assignments.append(default_assignment)

        return assignments

    async def _create_default_assignment(
        self, review: Review, session: Session | AsyncSession
    ) -> Optional[ReviewAssignment]:
        """Create a default assignment using configured default reviewers.

        Args:
            review: Review to assign
            session: Database session

        Returns:
            ReviewAssignment object or None
        """
        default_reviewers = self.config.default_reviewers

        if not default_reviewers:
            return None

        # Assign to first default reviewer
        assignment = ReviewAssignment(
            review_id=review.id,
            reviewer_identifier=default_reviewers[0],
        )

        session.add(assignment)

        if isinstance(session, AsyncSession):
            await session.flush()
        else:
            session.flush()

        return assignment
