"""Connector manager for orchestrating review notifications."""
import logging
from typing import Any, Dict, List, Optional, Type

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from .connector_models import ConnectorConfig, NotificationLog
from .connectors import ReviewConnector, SlackConnector
from .models import Decision, Review
from .routing import RoutingEngine

logger = logging.getLogger(__name__)


class ConnectorManager:
    """Central service for managing connectors and routing notifications.

    The ConnectorManager:
    - Registers and manages connector instances
    - Routes reviews to appropriate connectors using RoutingEngine
    - Tracks notification delivery status
    - Handles both review notifications and decision updates
    """

    # Registry of available connector types
    CONNECTOR_TYPES: Dict[str, Type[ReviewConnector]] = {
        'slack': SlackConnector,
        # Add more connectors here as they're implemented:
        # 'email': EmailConnector,
        # 'webhook': WebhookConnector,
        # 'discord': DiscordConnector,
    }

    def __init__(self, session: AsyncSession):
        """Initialize connector manager.

        Args:
            session: SQLAlchemy async session
        """
        self.session = session
        self.routing_engine = RoutingEngine(session)
        self._connector_cache: Dict[int, ReviewConnector] = {}

    async def send_review_notification(
        self,
        review: Review,
        additional_context: Optional[Dict[str, Any]] = None
    ) -> List[NotificationLog]:
        """Send notifications for a new review to all matching connectors.

        Args:
            review: The review to notify about
            additional_context: Optional context (dashboard URL, etc.)

        Returns:
            List of notification logs created
        """
        # Use routing engine to determine where to send
        routes = await self.routing_engine.route_review(
            review,
            organization_id=review.organization_id
        )

        if not routes:
            logger.warning(f"No routes found for review {review.id}")
            return []

        notification_logs = []

        for connector_config, recipients in routes:
            try:
                # Get or create connector instance
                connector = await self._get_connector(connector_config)

                # Send notification
                result = await connector.send_review_notification(
                    review,
                    recipients,
                    additional_context
                )

                # Log the notification
                for recipient in recipients:
                    log = NotificationLog(
                        review_id=review.id,
                        connector_id=connector_config.id,
                        status='sent' if result['success'] else 'failed',
                        error_message=result.get('error'),
                        recipient=recipient,
                        message_id=result.get('message_id'),
                        notification_metadata={
                            'connector_type': connector_config.connector_type,
                            'result': result
                        }
                    )
                    self.session.add(log)
                    notification_logs.append(log)

                await self.session.commit()

                if result['success']:
                    logger.info(
                        f"Sent review {review.id} via {connector_config.connector_type} "
                        f"to {len(recipients)} recipients"
                    )
                else:
                    logger.error(
                        f"Failed to send review {review.id} via {connector_config.connector_type}: "
                        f"{result.get('error')}"
                    )

            except Exception as e:
                logger.error(
                    f"Error sending notification via {connector_config.connector_type}: {e}",
                    exc_info=True
                )

                # Still log the failure
                for recipient in recipients:
                    log = NotificationLog(
                        review_id=review.id,
                        connector_id=connector_config.id,
                        status='failed',
                        error_message=str(e),
                        recipient=recipient
                    )
                    self.session.add(log)
                    notification_logs.append(log)

                await self.session.commit()

        return notification_logs

    async def send_decision_notification(
        self,
        review: Review,
        decision: Decision
    ) -> List[NotificationLog]:
        """Send notifications about a completed decision.

        Args:
            review: The review that was decided on
            decision: The decision that was made

        Returns:
            List of notification logs created
        """
        # Use routing engine (same routes as original review)
        routes = await self.routing_engine.route_review(
            review,
            organization_id=review.organization_id
        )

        notification_logs = []

        for connector_config, recipients in routes:
            try:
                connector = await self._get_connector(connector_config)

                result = await connector.send_decision_notification(
                    review,
                    decision,
                    recipients
                )

                for recipient in recipients:
                    log = NotificationLog(
                        review_id=review.id,
                        connector_id=connector_config.id,
                        status='sent' if result['success'] else 'failed',
                        error_message=result.get('error'),
                        recipient=recipient,
                        message_id=result.get('message_id'),
                        notification_metadata={
                            'connector_type': connector_config.connector_type,
                            'decision_type': decision.decision_type,
                            'result': result
                        }
                    )
                    self.session.add(log)
                    notification_logs.append(log)

                await self.session.commit()

                if result['success']:
                    logger.info(
                        f"Sent decision notification for review {review.id} "
                        f"via {connector_config.connector_type}"
                    )

            except Exception as e:
                logger.error(
                    f"Error sending decision notification via {connector_config.connector_type}: {e}",
                    exc_info=True
                )

        return notification_logs

    async def create_connector(
        self,
        connector_type: str,
        name: str,
        config_data: Dict[str, Any],
        organization_id: Optional[int] = None
    ) -> ConnectorConfig:
        """Create and register a new connector.

        Args:
            connector_type: Type of connector ('slack', 'email', etc.)
            name: Human-readable name
            config_data: Connector configuration (API keys, etc.)
            organization_id: Optional organization ID

        Returns:
            Created connector config

        Raises:
            ValueError: If connector_type is not supported
        """
        if connector_type not in self.CONNECTOR_TYPES:
            raise ValueError(
                f"Unsupported connector type: {connector_type}. "
                f"Available: {list(self.CONNECTOR_TYPES.keys())}"
            )

        # Test the connector before saving
        connector_class = self.CONNECTOR_TYPES[connector_type]
        connector = connector_class(config_data)

        test_result = await connector.test_connection()
        if not test_result['success']:
            raise ValueError(f"Connector test failed: {test_result['message']}")

        # Create config
        config = ConnectorConfig(
            connector_type=connector_type,
            name=name,
            config_data=config_data,
            organization_id=organization_id,
            enabled=True
        )

        self.session.add(config)
        await self.session.commit()
        await self.session.refresh(config)

        logger.info(f"Created connector: {name} ({connector_type})")
        return config

    async def get_connector_config(self, connector_id: int) -> Optional[ConnectorConfig]:
        """Get a connector configuration by ID.

        Args:
            connector_id: Connector ID

        Returns:
            Connector config or None
        """
        return await self.session.get(ConnectorConfig, connector_id)

    async def list_connectors(
        self,
        organization_id: Optional[int] = None,
        enabled_only: bool = True
    ) -> List[ConnectorConfig]:
        """List all connectors.

        Args:
            organization_id: Optional filter by organization
            enabled_only: Only return enabled connectors

        Returns:
            List of connector configs
        """
        query = select(ConnectorConfig)

        if organization_id:
            query = query.where(
                (ConnectorConfig.organization_id == organization_id) |
                (ConnectorConfig.organization_id.is_(None))
            )

        if enabled_only:
            query = query.where(ConnectorConfig.enabled == True)

        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def update_connector(
        self,
        connector_id: int,
        **updates
    ) -> Optional[ConnectorConfig]:
        """Update a connector configuration.

        Args:
            connector_id: Connector ID
            **updates: Fields to update

        Returns:
            Updated connector or None
        """
        config = await self.session.get(ConnectorConfig, connector_id)
        if not config:
            return None

        for key, value in updates.items():
            if hasattr(config, key):
                setattr(config, key, value)

        # If config_data was updated, clear cache
        if 'config_data' in updates and connector_id in self._connector_cache:
            del self._connector_cache[connector_id]

        await self.session.commit()
        await self.session.refresh(config)

        logger.info(f"Updated connector {connector_id}: {config.name}")
        return config

    async def delete_connector(self, connector_id: int) -> bool:
        """Delete a connector.

        Args:
            connector_id: Connector ID

        Returns:
            True if deleted, False if not found
        """
        config = await self.session.get(ConnectorConfig, connector_id)
        if not config:
            return False

        # Clear from cache
        if connector_id in self._connector_cache:
            del self._connector_cache[connector_id]

        await self.session.delete(config)
        await self.session.commit()

        logger.info(f"Deleted connector {connector_id}")
        return True

    async def test_connector(self, connector_id: int) -> Dict[str, Any]:
        """Test a connector connection.

        Args:
            connector_id: Connector ID

        Returns:
            Test result dict
        """
        config = await self.session.get(ConnectorConfig, connector_id)
        if not config:
            return {"success": False, "message": "Connector not found"}

        try:
            connector = await self._get_connector(config)
            return await connector.test_connection()
        except Exception as e:
            return {"success": False, "message": f"Error: {str(e)}"}

    async def _get_connector(self, config: ConnectorConfig) -> ReviewConnector:
        """Get or create a connector instance from configuration.

        Args:
            config: Connector configuration

        Returns:
            Connector instance

        Raises:
            ValueError: If connector type is not supported
        """
        # Check cache first
        if config.id in self._connector_cache:
            return self._connector_cache[config.id]

        # Get connector class
        connector_class = self.CONNECTOR_TYPES.get(config.connector_type)
        if not connector_class:
            raise ValueError(f"Unsupported connector type: {config.connector_type}")

        # Create instance
        connector = connector_class(config.config_data)

        # Cache it
        self._connector_cache[config.id] = connector

        return connector
