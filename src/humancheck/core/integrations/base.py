"""Base connector interface for communication channels."""
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional

from ..models import Decision, Review


class ReviewConnector(ABC):
    """Base abstract class for review notification connectors.

    Connectors handle sending review notifications and decisions through
    various communication channels (Slack, email, webhooks, etc.)
    """

    def __init__(self, config: Dict[str, Any]):
        """Initialize connector with configuration.

        Args:
            config: Connector-specific configuration (API keys, endpoints, etc.)
        """
        self.config = config
        self.connector_type = self._get_connector_type()

    @abstractmethod
    def _get_connector_type(self) -> str:
        """Return the connector type identifier (e.g., 'slack', 'email')."""
        pass

    @abstractmethod
    async def send_review_notification(
        self,
        review: Review,
        recipients: List[str],
        additional_context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Send a notification about a pending review.

        Args:
            review: The review to notify about
            recipients: List of recipient identifiers (channels, emails, etc.)
            additional_context: Optional extra data for the notification

        Returns:
            Dict with status and message_id:
            {
                'success': True/False,
                'message_id': 'external_message_id',
                'error': 'error message if failed'
            }
        """
        pass

    @abstractmethod
    async def send_decision_notification(
        self,
        review: Review,
        decision: Decision,
        recipients: List[str]
    ) -> Dict[str, Any]:
        """Send a notification about a completed decision.

        Args:
            review: The review that was decided on
            decision: The decision that was made
            recipients: List of recipient identifiers

        Returns:
            Dict with status and message_id
        """
        pass

    async def update_notification(
        self,
        message_id: str,
        review: Review,
        decision: Optional[Decision] = None
    ) -> Dict[str, Any]:
        """Update an existing notification (optional, for interactive channels).

        Args:
            message_id: External message ID to update
            review: Updated review data
            decision: Decision if one was made

        Returns:
            Dict with success status
        """
        return {'success': True, 'message': 'Update not supported for this connector'}

    async def test_connection(self) -> Dict[str, Any]:
        """Test if the connector is properly configured.

        Returns:
            Dict with connection status:
            {
                'success': True/False,
                'message': 'status message'
            }
        """
        return {'success': True, 'message': 'No test implemented'}

    def format_review_message(self, review: Review) -> str:
        """Format a review into a human-readable message.

        Args:
            review: The review to format

        Returns:
            Formatted string representation
        """
        urgency_emoji = {
            'low': '🟢',
            'medium': '🟡',
            'high': '🟠',
            'critical': '🔴'
        }

        emoji = urgency_emoji.get(review.urgency, '⚪')

        message = f"""{emoji} New Review Request

**Task Type:** {review.task_type}
**Urgency:** {review.urgency.upper()}
**Proposed Action:**
{review.proposed_action}
"""

        if review.agent_reasoning:
            message += f"\n**Agent Reasoning:**\n{review.agent_reasoning}\n"

        if review.confidence_score:
            message += f"\n**Confidence:** {review.confidence_score:.1%}\n"

        return message

    def format_decision_message(self, review: Review, decision: Decision) -> str:
        """Format a decision into a human-readable message.

        Args:
            review: The review that was decided on
            decision: The decision that was made

        Returns:
            Formatted string representation
        """
        decision_emoji = {
            'approve': '✅',
            'reject': '❌',
            'modify': '✏️'
        }

        emoji = decision_emoji.get(decision.decision_type, '📋')

        message = f"""{emoji} Decision: {decision.decision_type.upper()}

**Task Type:** {review.task_type}
**Original Action:** {review.proposed_action}
"""

        if decision.modified_action:
            message += f"\n**Modified Action:** {decision.modified_action}\n"

        if decision.notes:
            message += f"\n**Notes:** {decision.notes}\n"

        return message
