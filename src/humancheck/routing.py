"""Routing engine for directing reviews to appropriate connectors."""
import logging
from typing import Dict, List, Optional, Tuple

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from .connector_models import ConnectorConfig, ConnectorRoutingRule
from .models import Review

logger = logging.getLogger(__name__)


class RoutingEngine:
    """Engine for evaluating routing rules and determining which connectors to notify.

    The routing engine evaluates rules in priority order and matches reviews
    based on their attributes (task_type, urgency, framework, etc.)
    """

    def __init__(self, session: AsyncSession):
        """Initialize routing engine with database session.

        Args:
            session: SQLAlchemy async session
        """
        self.session = session

    async def route_review(
        self,
        review: Review,
        organization_id: Optional[int] = None
    ) -> List[Tuple[ConnectorConfig, List[str]]]:
        """Determine which connectors should be notified for a review.

        Args:
            review: The review to route
            organization_id: Optional organization ID for multi-tenancy

        Returns:
            List of (connector, recipients) tuples to notify
        """
        # Get all enabled routing rules, ordered by priority
        query = (
            select(ConnectorRoutingRule)
            .where(ConnectorRoutingRule.enabled == True)
            .order_by(ConnectorRoutingRule.priority.desc())
        )

        # Filter by organization if provided
        if organization_id:
            query = query.where(
                (ConnectorRoutingRule.organization_id == organization_id) |
                (ConnectorRoutingRule.organization_id.is_(None))
            )

        result = await self.session.execute(query)
        rules = result.scalars().all()

        # Evaluate rules and collect matching connectors
        matched_routes: Dict[int, List[str]] = {}  # connector_id -> recipients

        for rule in rules:
            if self._evaluate_rule(review, rule):
                logger.info(f"Review {review.id} matched rule: {rule.name}")

                # Get or initialize recipients list for this connector
                if rule.connector_id not in matched_routes:
                    matched_routes[rule.connector_id] = []

                # Add recipients from this rule
                matched_routes[rule.connector_id].extend(rule.recipients)

        # Fetch connector configs
        routes = []
        for connector_id, recipients in matched_routes.items():
            connector = await self.session.get(ConnectorConfig, connector_id)
            if connector and connector.enabled:
                # Deduplicate recipients
                unique_recipients = list(set(recipients))
                routes.append((connector, unique_recipients))
                logger.info(
                    f"Review {review.id} will be sent via {connector.connector_type} "
                    f"to {len(unique_recipients)} recipients"
                )

        return routes

    def _evaluate_rule(self, review: Review, rule: ConnectorRoutingRule) -> bool:
        """Evaluate if a review matches a routing rule's conditions.

        Args:
            review: The review to evaluate
            rule: The routing rule to check

        Returns:
            True if review matches all rule conditions
        """
        conditions = rule.conditions

        # If no conditions, match everything (catch-all rule)
        if not conditions:
            return True

        # Check task_type condition
        if "task_type" in conditions:
            task_types = conditions["task_type"]
            if isinstance(task_types, str):
                task_types = [task_types]
            if review.task_type not in task_types:
                return False

        # Check urgency condition
        if "urgency" in conditions:
            urgencies = conditions["urgency"]
            if isinstance(urgencies, str):
                urgencies = [urgencies]
            if review.urgency not in urgencies:
                return False

        # Check framework condition
        if "framework" in conditions:
            frameworks = conditions["framework"]
            if isinstance(frameworks, str):
                frameworks = [frameworks]
            if review.framework not in frameworks:
                return False

        # Check confidence_score condition (threshold)
        if "min_confidence" in conditions:
            min_confidence = float(conditions["min_confidence"])
            if review.confidence_score is None or review.confidence_score < min_confidence:
                return False

        if "max_confidence" in conditions:
            max_confidence = float(conditions["max_confidence"])
            if review.confidence_score is None or review.confidence_score > max_confidence:
                return False

        # Check custom metadata conditions
        if "metadata" in conditions and review.meta_data:
            metadata_conditions = conditions["metadata"]
            for key, expected_value in metadata_conditions.items():
                actual_value = review.meta_data.get(key)
                if isinstance(expected_value, list):
                    if actual_value not in expected_value:
                        return False
                else:
                    if actual_value != expected_value:
                        return False

        # All conditions matched
        return True

    async def create_rule(
        self,
        connector_id: int,
        name: str,
        conditions: Dict,
        recipients: List[str],
        priority: int = 0,
        organization_id: Optional[int] = None
    ) -> ConnectorRoutingRule:
        """Create a new routing rule.

        Args:
            connector_id: ID of the connector to route to
            name: Human-readable name for the rule
            conditions: Dict of conditions to match
            recipients: List of recipient identifiers
            priority: Priority (higher = evaluated first)
            organization_id: Optional organization ID

        Returns:
            Created routing rule
        """
        rule = ConnectorRoutingRule(
            connector_id=connector_id,
            name=name,
            conditions=conditions,
            recipients=recipients,
            priority=priority,
            organization_id=organization_id,
            enabled=True
        )

        self.session.add(rule)
        await self.session.commit()
        await self.session.refresh(rule)

        logger.info(f"Created routing rule: {name} (priority={priority})")
        return rule

    async def get_rules_for_connector(
        self,
        connector_id: int
    ) -> List[ConnectorRoutingRule]:
        """Get all routing rules for a specific connector.

        Args:
            connector_id: Connector ID

        Returns:
            List of routing rules
        """
        query = (
            select(ConnectorRoutingRule)
            .where(ConnectorRoutingRule.connector_id == connector_id)
            .order_by(ConnectorRoutingRule.priority.desc())
        )

        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def update_rule(
        self,
        rule_id: int,
        **updates
    ) -> Optional[ConnectorRoutingRule]:
        """Update a routing rule.

        Args:
            rule_id: ID of rule to update
            **updates: Fields to update

        Returns:
            Updated rule or None if not found
        """
        rule = await self.session.get(ConnectorRoutingRule, rule_id)
        if not rule:
            return None

        for key, value in updates.items():
            if hasattr(rule, key):
                setattr(rule, key, value)

        await self.session.commit()
        await self.session.refresh(rule)

        logger.info(f"Updated routing rule {rule_id}: {rule.name}")
        return rule

    async def delete_rule(self, rule_id: int) -> bool:
        """Delete a routing rule.

        Args:
            rule_id: ID of rule to delete

        Returns:
            True if deleted, False if not found
        """
        rule = await self.session.get(ConnectorRoutingRule, rule_id)
        if not rule:
            return False

        await self.session.delete(rule)
        await self.session.commit()

        logger.info(f"Deleted routing rule {rule_id}")
        return True


# Example routing rule configurations:
#
# Route all SQL execution reviews to #database-team on Slack:
# {
#     "task_type": "tool_call_execute_sql",
#     "urgency": ["high", "critical"]
# }
# recipients: ["#database-team"]
#
# Route low confidence reviews to human reviewers:
# {
#     "max_confidence": 0.7
# }
# recipients: ["#review-queue"]
#
# Route critical reviews to PagerDuty:
# {
#     "urgency": "critical"
# }
# recipients: ["pagerduty-integration-key"]
