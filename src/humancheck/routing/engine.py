"""Routing engine for intelligent review assignment."""
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session

from ..models import Review, ReviewAssignment
from ..platform_models import RoutingRule, Team, User
from .evaluator import ConditionEvaluator


class RoutingEngine:
    """Engine for routing reviews to appropriate reviewers based on rules.

    The routing engine evaluates rules in priority order and assigns reviews
    to users or teams based on matching conditions.
    """

    def __init__(self):
        """Initialize the routing engine."""
        self.evaluator = ConditionEvaluator()

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
        # Get applicable routing rules for this organization
        rules = await self._get_routing_rules(review.organization_id, session)

        # Prepare review data for evaluation
        review_data = {
            "task_type": review.task_type,
            "confidence_score": review.confidence_score,
            "urgency": review.urgency,
            "framework": review.framework,
            "agent_id": review.agent_id,
            "metadata": review.meta_data or {},
        }

        assignments = []

        # Evaluate rules in priority order
        for rule in rules:
            if not rule.is_active:
                continue

            # Check if conditions match
            if self.evaluator.evaluate(rule.conditions, review_data):
                # Create assignment
                assignment = await self._create_assignment(review, rule, session)
                if assignment:
                    assignments.append(assignment)

                # Stop after first match (can be changed to process all matches)
                break

        # If no rules matched, use default assignment
        if not assignments:
            default_assignment = await self._create_default_assignment(review, session)
            if default_assignment:
                assignments.append(default_assignment)

        return assignments

    async def _get_routing_rules(
        self, organization_id: Optional[int], session: Session | AsyncSession
    ) -> list[RoutingRule]:
        """Get routing rules for an organization, ordered by priority.

        Args:
            organization_id: Organization ID
            session: Database session

        Returns:
            List of routing rules ordered by priority (highest first)
        """
        if organization_id is None:
            return []

        if isinstance(session, AsyncSession):
            result = await session.execute(
                select(RoutingRule)
                .where(RoutingRule.organization_id == organization_id)
                .order_by(RoutingRule.priority.desc())
            )
            return list(result.scalars().all())
        else:
            return (
                session.query(RoutingRule)
                .filter(RoutingRule.organization_id == organization_id)
                .order_by(RoutingRule.priority.desc())
                .all()
            )

    async def _create_assignment(
        self, review: Review, rule: RoutingRule, session: Session | AsyncSession
    ) -> Optional[ReviewAssignment]:
        """Create a review assignment based on a routing rule.

        Args:
            review: Review to assign
            rule: Routing rule that matched
            session: Database session

        Returns:
            ReviewAssignment object or None
        """
        assignment = ReviewAssignment(
            review_id=review.id,
            user_id=rule.assign_to_user_id,
            team_id=rule.assign_to_team_id,
            assigned_by_rule_id=rule.id,
        )

        session.add(assignment)

        if isinstance(session, AsyncSession):
            await session.flush()
        else:
            session.flush()

        return assignment

    async def _create_default_assignment(
        self, review: Review, session: Session | AsyncSession
    ) -> Optional[ReviewAssignment]:
        """Create a default assignment when no rules match.

        This assigns to the first admin user in the organization.

        Args:
            review: Review to assign
            session: Database session

        Returns:
            ReviewAssignment object or None
        """
        if review.organization_id is None:
            return None

        # Find first admin user in the organization
        if isinstance(session, AsyncSession):
            result = await session.execute(
                select(User)
                .where(User.organization_id == review.organization_id)
                .where(User.role == "admin")
                .where(User.is_active == True)
                .limit(1)
            )
            admin_user = result.scalar_one_or_none()
        else:
            admin_user = (
                session.query(User)
                .filter(User.organization_id == review.organization_id)
                .filter(User.role == "admin")
                .filter(User.is_active == True)
                .first()
            )

        if admin_user is None:
            return None

        assignment = ReviewAssignment(
            review_id=review.id,
            user_id=admin_user.id,
            assigned_by_rule_id=None,  # No rule, default assignment
        )

        session.add(assignment)

        if isinstance(session, AsyncSession):
            await session.flush()
        else:
            session.flush()

        return assignment

    async def get_assigned_users(
        self, review_id: int, session: Session | AsyncSession
    ) -> list[User]:
        """Get all users assigned to a review (directly or via team).

        Args:
            review_id: Review ID
            session: Database session

        Returns:
            List of User objects
        """
        users = []

        # Get assignments
        if isinstance(session, AsyncSession):
            result = await session.execute(
                select(ReviewAssignment)
                .where(ReviewAssignment.review_id == review_id)
            )
            assignments = list(result.scalars().all())
        else:
            assignments = (
                session.query(ReviewAssignment)
                .filter(ReviewAssignment.review_id == review_id)
                .all()
            )

        for assignment in assignments:
            # Direct user assignment
            if assignment.user_id:
                if isinstance(session, AsyncSession):
                    user = await session.get(User, assignment.user_id)
                else:
                    user = session.query(User).get(assignment.user_id)
                if user:
                    users.append(user)

            # Team assignment - get all team members
            if assignment.team_id:
                if isinstance(session, AsyncSession):
                    team = await session.get(Team, assignment.team_id)
                else:
                    team = session.query(Team).get(assignment.team_id)

                if team:
                    for membership in team.memberships:
                        if membership.user.is_active:
                            users.append(membership.user)

        # Remove duplicates
        seen = set()
        unique_users = []
        for user in users:
            if user.id not in seen:
                seen.add(user.id)
                unique_users.append(user)

        return unique_users
