"""Slack connector for sending review notifications."""
import logging
from typing import Any, Dict, List, Optional

from slack_sdk.web.async_client import AsyncWebClient
from slack_sdk.errors import SlackApiError

from ..base import ReviewConnector
from ...models import Decision, Review

logger = logging.getLogger(__name__)


class SlackConnector(ReviewConnector):
    """Slack connector for sending review notifications to Slack channels.

    Config format:
    {
        "bot_token": "xoxb-...",  # Slack bot token
        "app_token": "xapp-..." (optional),  # For socket mode
        "signing_secret": "..." (optional)  # For webhook verification
    }
    """

    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.client = AsyncWebClient(token=config.get("bot_token"))

    def _get_connector_type(self) -> str:
        return "slack"

    async def send_review_notification(
        self,
        review: Review,
        recipients: List[str],
        additional_context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Send a Slack message about a pending review.

        Args:
            review: The review to notify about
            recipients: List of Slack channel IDs or names (e.g., ["#reviews", "C01234567"])
            additional_context: Optional dashboard URL, etc.

        Returns:
            Dict with success status and message_id (Slack timestamp)
        """
        try:
            # Build Slack blocks for rich formatting
            blocks = self._build_review_blocks(review, additional_context)

            results = []
            for recipient in recipients:
                # Post message to channel
                response = await self.client.chat_postMessage(
                    channel=recipient,
                    blocks=blocks,
                    text=f"New review request: {review.task_type}"  # Fallback text
                )

                if response["ok"]:
                    results.append({
                        "recipient": recipient,
                        "message_id": response["ts"],  # Slack timestamp serves as message ID
                        "channel": response["channel"]
                    })
                    logger.info(f"Sent Slack notification for review {review.id} to {recipient}")
                else:
                    logger.error(f"Failed to send Slack notification: {response.get('error')}")

            if results:
                return {
                    "success": True,
                    "message_id": results[0]["message_id"],  # Primary message ID
                    "results": results
                }
            else:
                return {
                    "success": False,
                    "error": "No messages sent successfully"
                }

        except SlackApiError as e:
            logger.error(f"Slack API error: {e.response['error']}")
            return {
                "success": False,
                "error": f"Slack API error: {e.response['error']}"
            }
        except Exception as e:
            logger.error(f"Unexpected error sending Slack notification: {e}")
            return {
                "success": False,
                "error": str(e)
            }

    async def send_decision_notification(
        self,
        review: Review,
        decision: Decision,
        recipients: List[str]
    ) -> Dict[str, Any]:
        """Send a Slack message about a completed decision.

        Args:
            review: The review that was decided on
            decision: The decision that was made
            recipients: List of Slack channel IDs or names

        Returns:
            Dict with success status and message_id
        """
        try:
            blocks = self._build_decision_blocks(review, decision)

            results = []
            for recipient in recipients:
                response = await self.client.chat_postMessage(
                    channel=recipient,
                    blocks=blocks,
                    text=f"Decision made: {decision.decision_type} - {review.task_type}"
                )

                if response["ok"]:
                    results.append({
                        "recipient": recipient,
                        "message_id": response["ts"],
                        "channel": response["channel"]
                    })

            if results:
                return {
                    "success": True,
                    "message_id": results[0]["message_id"],
                    "results": results
                }
            else:
                return {
                    "success": False,
                    "error": "No messages sent successfully"
                }

        except SlackApiError as e:
            logger.error(f"Slack API error: {e.response['error']}")
            return {
                "success": False,
                "error": f"Slack API error: {e.response['error']}"
            }

    async def update_notification(
        self,
        message_id: str,
        review: Review,
        decision: Optional[Decision] = None
    ) -> Dict[str, Any]:
        """Update an existing Slack message with decision information.

        Args:
            message_id: Slack message timestamp (ts)
            review: Updated review data
            decision: Decision if one was made

        Returns:
            Dict with success status
        """
        try:
            # Find the channel from notification logs
            # For now, we'll need to store channel info in metadata
            # This is a simplified version
            blocks = self._build_decision_blocks(review, decision) if decision else self._build_review_blocks(review, {})

            # Note: We need the channel ID to update. In production, store this in NotificationLog metadata
            # For now, this is a placeholder
            return {
                "success": True,
                "message": "Update would happen here with proper channel tracking"
            }

        except SlackApiError as e:
            logger.error(f"Slack API error updating message: {e.response['error']}")
            return {
                "success": False,
                "error": f"Slack API error: {e.response['error']}"
            }

    async def test_connection(self) -> Dict[str, Any]:
        """Test the Slack connection by calling auth.test.

        Returns:
            Dict with connection status and bot info
        """
        try:
            response = await self.client.auth_test()
            if response["ok"]:
                return {
                    "success": True,
                    "message": f"Connected as {response['user']} to {response['team']}",
                    "bot_id": response.get("user_id"),
                    "team": response.get("team")
                }
            else:
                return {
                    "success": False,
                    "message": f"Connection failed: {response.get('error')}"
                }
        except SlackApiError as e:
            return {
                "success": False,
                "message": f"Slack API error: {e.response['error']}"
            }
        except Exception as e:
            return {
                "success": False,
                "message": f"Error: {str(e)}"
            }

    def _build_review_blocks(self, review: Review, context: Optional[Dict[str, Any]] = None) -> List[Dict]:
        """Build Slack Block Kit blocks for a review notification.

        Args:
            review: The review to format
            context: Optional additional context (dashboard URL, etc.)

        Returns:
            List of Slack Block Kit blocks
        """
        urgency_emoji = {
            'low': '🟢',
            'medium': '🟡',
            'high': '🟠',
            'critical': '🔴'
        }

        emoji = urgency_emoji.get(review.urgency, '⚪')

        blocks = [
            {
                "type": "header",
                "text": {
                    "type": "plain_text",
                    "text": f"{emoji} New Review Request"
                }
            },
            {
                "type": "section",
                "fields": [
                    {
                        "type": "mrkdwn",
                        "text": f"*Task Type:*\n{review.task_type}"
                    },
                    {
                        "type": "mrkdwn",
                        "text": f"*Urgency:*\n{review.urgency.upper()}"
                    }
                ]
            },
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"*Proposed Action:*\n```{review.proposed_action}```"
                }
            }
        ]

        # Add agent reasoning if available
        if review.agent_reasoning:
            blocks.append({
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"*Agent Reasoning:*\n{review.agent_reasoning}"
                }
            })

        # Add confidence score if available
        if review.confidence_score:
            blocks.append({
                "type": "context",
                "elements": [
                    {
                        "type": "mrkdwn",
                        "text": f"Confidence: {review.confidence_score:.1%}"
                    }
                ]
            })

        # Add dashboard link if provided
        if context and context.get("dashboard_url"):
            blocks.append({
                "type": "actions",
                "elements": [
                    {
                        "type": "button",
                        "text": {
                            "type": "plain_text",
                            "text": "View in Dashboard"
                        },
                        "url": context["dashboard_url"],
                        "style": "primary"
                    }
                ]
            })

        return blocks

    def _build_decision_blocks(self, review: Review, decision: Decision) -> List[Dict]:
        """Build Slack Block Kit blocks for a decision notification.

        Args:
            review: The review that was decided on
            decision: The decision that was made

        Returns:
            List of Slack Block Kit blocks
        """
        decision_emoji = {
            'approve': '✅',
            'reject': '❌',
            'modify': '✏️'
        }

        emoji = decision_emoji.get(decision.decision_type, '📋')

        blocks = [
            {
                "type": "header",
                "text": {
                    "type": "plain_text",
                    "text": f"{emoji} Decision: {decision.decision_type.upper()}"
                }
            },
            {
                "type": "section",
                "fields": [
                    {
                        "type": "mrkdwn",
                        "text": f"*Task Type:*\n{review.task_type}"
                    },
                    {
                        "type": "mrkdwn",
                        "text": f"*Review ID:*\n#{review.id}"
                    }
                ]
            },
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"*Original Action:*\n```{review.proposed_action}```"
                }
            }
        ]

        # Add modified action if present
        if decision.modified_action:
            blocks.append({
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"*Modified Action:*\n```{decision.modified_action}```"
                }
            })

        # Add notes if present
        if decision.notes:
            blocks.append({
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"*Notes:*\n{decision.notes}"
                }
            })

        return blocks
