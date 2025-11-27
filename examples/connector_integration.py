"""Example of integrating connectors with review creation flow.

This shows how to:
1. Create and configure connectors
2. Set up routing rules
3. Send notifications when reviews are created/decided
"""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from humancheck.core.config.settings import init_config
from humancheck.core.integrations.manager import ConnectorManager
from humancheck.core.storage.database import init_db
from humancheck.core.models import DecisionType, Review, ReviewStatus, UrgencyLevel


async def setup_example_connector_and_rules():
    """Set up a Slack connector and routing rules."""
    config = init_config()
    db = init_db(config.get_database_url())

    async with db.session() as session:
        manager = ConnectorManager(session)

        # 1. Create a Slack connector
        print("Creating Slack connector...")
        try:
            slack_connector = await manager.create_connector(
                connector_type='slack',
                name='Team Slack Workspace',
                config_data={
                    'bot_token': 'xapp-1-A09QPDH1ZRR-9839466501683-fe43b1c78aab3f185fbface151e72c361f451760ef9244ec6b384788af0d2bf5'  # Replace with real token
                }
            )
            print(f"✅ Created Slack connector: {slack_connector.name} (ID: {slack_connector.id})")
        except ValueError as e:
            print(f"❌ Failed to create connector: {e}")
            print("Skipping connector creation (it may already exist or token is invalid)")
            # For demo purposes, let's assume connector ID 1 exists
            slack_connector = await manager.get_connector_config(1)
            if not slack_connector:
                print("No connector found. Please set up a real Slack bot token.")
                return

        # 2. Create routing rules
        print("\nCreating routing rules...")

        # Rule 1: Route SQL execution reviews to #database-team
        rule1 = await manager.routing_engine.create_rule(
            connector_id=slack_connector.id,
            name="SQL Reviews to DB Team",
            conditions={
                "task_type": "tool_call_execute_sql",
                "urgency": ["high", "critical"]
            },
            recipients=["#database-team"],
            priority=100
        )
        print(f"✅ Created rule: {rule1.name}")

        # Rule 2: Route all critical reviews to #urgent-reviews
        rule2 = await manager.routing_engine.create_rule(
            connector_id=slack_connector.id,
            name="Critical Reviews",
            conditions={
                "urgency": "critical"
            },
            recipients=["#urgent-reviews", "@oncall"],
            priority=200  # Higher priority = evaluated first
        )
        print(f"✅ Created rule: {rule2.name}")

        # Rule 3: Route low confidence reviews to #review-queue
        rule3 = await manager.routing_engine.create_rule(
            connector_id=slack_connector.id,
            name="Low Confidence Reviews",
            conditions={
                "max_confidence": 0.7
            },
            recipients=["#review-queue"],
            priority=50
        )
        print(f"✅ Created rule: {rule3.name}")

        print("\n✅ Setup complete!")


async def example_send_review_notification():
    """Example: Send a notification when a review is created."""
    config = init_config()
    db = init_db(config.get_database_url())

    async with db.session() as session:
        manager = ConnectorManager(session)

        # Get a review (or create a test one)
        from sqlalchemy import select

        result = await session.execute(
            select(Review).where(Review.status == ReviewStatus.PENDING.value).limit(1)
        )
        review = result.scalar_one_or_none()

        if not review:
            print("No pending reviews found. Creating a test review...")
            review = Review(
                task_type="tool_call_execute_sql",
                proposed_action="DELETE FROM users WHERE inactive = true",
                agent_reasoning="Cleaning up inactive users to free up space",
                confidence_score=0.85,
                urgency=UrgencyLevel.HIGH.value,
                status=ReviewStatus.PENDING.value,
                framework="langgraph"
            )
            session.add(review)
            await session.commit()
            await session.refresh(review)

        print(f"\nSending notification for review #{review.id}...")

        # Send notification through all matching connectors
        logs = await manager.send_review_notification(
            review,
            additional_context={
                "dashboard_url": f"http://localhost:8502?review_id={review.id}"
            }
        )

        print(f"✅ Sent {len(logs)} notifications")
        for log in logs:
            status_emoji = "✅" if log.status == "sent" else "❌"
            print(f"  {status_emoji} {log.recipient} via connector #{log.connector_id}")


async def example_send_decision_notification():
    """Example: Send a notification when a decision is made."""
    config = init_config()
    db = init_db(config.get_database_url())

    async with db.session() as session:
        manager = ConnectorManager(session)

        # Get a review with a decision
        from sqlalchemy import select
        from humancheck.core.models import Decision

        result = await session.execute(
            select(Review)
            .join(Decision)
            .where(Review.status != ReviewStatus.PENDING.value)
            .limit(1)
        )
        review = result.scalar_one_or_none()

        if not review:
            print("No completed reviews found")
            return

        # Get the decision
        decision_result = await session.execute(
            select(Decision).where(Decision.review_id == review.id)
        )
        decision = decision_result.scalar_one()

        print(f"\nSending decision notification for review #{review.id}...")

        logs = await manager.send_decision_notification(review, decision)

        print(f"✅ Sent {len(logs)} decision notifications")
        for log in logs:
            status_emoji = "✅" if log.status == "sent" else "❌"
            print(f"  {status_emoji} {log.recipient}")


async def integration_example():
    """Complete integration example showing how to use connectors in your app."""
    print("=" * 60)
    print("Connector Integration Example")
    print("=" * 60)

    # Step 1: Setup (do this once during app initialization)
    print("\n📋 Step 1: Setting up connectors and rules...")
    await setup_example_connector_and_rules()

    # Step 2: Send review notification (when review is created)
    print("\n📋 Step 2: Sending review notification...")
    await example_send_review_notification()

    # Step 3: Send decision notification (when decision is made)
    print("\n📋 Step 3: Sending decision notification...")
    await example_send_decision_notification()

    print("\n" + "=" * 60)
    print("✅ Integration example complete!")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(integration_example())
