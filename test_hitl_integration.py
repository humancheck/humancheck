"""Test script to validate HITL integration."""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "src"))


async def test_hitl_integration():
    """Test the HITL integration by creating reviews and checking they were created."""
    from humancheck.config import init_config
    from humancheck.database import init_db
    from humancheck.adapters.langchain_hitl import LangChainHITLAdapter
    from humancheck.api import create_review
    from humancheck.models import Review
    from sqlalchemy import select

    print("=" * 70)
    print("Testing LangChain HITL Integration")
    print("=" * 70)

    # Initialize
    print("\n1. Initializing database...")
    config = init_config()
    db = init_db(config.get_database_url())
    await db.create_tables()
    print("   ✅ Database initialized")

    # Create adapter
    print("\n2. Creating HITL adapter...")
    adapter = LangChainHITLAdapter(db.session)
    print("   ✅ Adapter created")

    # Create test HITL interrupt
    print("\n3. Creating test HITL interrupt...")
    hitl_interrupt = {
        "action_requests": [
            {
                "name": "execute_sql",
                "arguments": {
                    "query": "DELETE FROM users WHERE created_at < NOW() - INTERVAL '30 days';"
                },
                "description": "Tool execution pending approval\n\nTool: execute_sql"
            },
            {
                "name": "send_email",
                "arguments": {
                    "to": "admin@example.com",
                    "subject": "Test email",
                    "body": "This is a test"
                },
                "description": "Tool execution pending approval\n\nTool: send_email"
            }
        ],
        "review_configs": [
            {
                "action_name": "execute_sql",
                "allowed_decisions": ["approve", "reject"]
            },
            {
                "action_name": "send_email",
                "allowed_decisions": ["approve", "edit", "reject"]
            }
        ],
        "thread_id": "test-thread-123",
        "config": {},
        "urgency": "high"
    }
    print("   ✅ HITL interrupt created")

    # Convert to reviews
    print("\n4. Converting to UniversalReview format...")
    reviews = adapter.to_universal(hitl_interrupt)
    print(f"   ✅ Created {len(reviews)} review(s)")

    # Verify review structure
    print("\n5. Verifying review structure...")
    assert len(reviews) == 2, f"Expected 2 reviews, got {len(reviews)}"

    for i, review in enumerate(reviews):
        print(f"\n   Review {i+1}:")
        print(f"     - Task Type: {review.task_type}")
        print(f"     - Framework: {review.framework}")
        print(f"     - Urgency: {review.urgency}")
        print(f"     - Metadata: {review.metadata.get('tool_name') if review.metadata else 'None'}")

        assert review.framework == "langchain_hitl"
        assert review.metadata is not None
        assert "tool_name" in review.metadata
        assert "tool_arguments" in review.metadata

    print("\n   ✅ Review structure validated")

    # Create reviews in database
    print("\n6. Creating reviews in database...")
    review_ids = []
    async with db.session() as session:
        for review in reviews:
            review_obj = await create_review(review, session)  # Fixed argument order
            review_ids.append(review_obj.id)
            await session.commit()
            print(f"   ✅ Created Review #{review_obj.id}: {review.task_type}")

    # Verify reviews were saved
    print("\n7. Verifying reviews in database...")
    async with db.session() as session:
        result = await session.execute(
            select(Review).where(Review.id.in_(review_ids))
        )
        saved_reviews = list(result.scalars().all())

        assert len(saved_reviews) == len(review_ids)
        print(f"   ✅ Verified {len(saved_reviews)} reviews in database")

        for saved_review in saved_reviews:
            print(f"\n   Review #{saved_review.id}:")
            print(f"     - Status: {saved_review.status}")
            print(f"     - Framework: {saved_review.framework}")
            print(f"     - Task Type: {saved_review.task_type}")
            print(f"     - Tool: {saved_review.meta_data.get('tool_name')}")
            print(f"     - Arguments: {saved_review.meta_data.get('tool_arguments')}")

    # Test decision conversion
    print("\n8. Testing decision conversion...")
    from humancheck.models import Decision, DecisionType

    # Create a mock decision
    async with db.session() as session:
        # Approve decision
        approve_decision = Decision(
            review_id=review_ids[0],
            decision_type=DecisionType.APPROVE.value,
            notes="Looks good"
        )
        session.add(approve_decision)
        await session.commit()

        # Get the review with decision
        review = await session.get(Review, review_ids[0])
        session.expunge(review)
        session.expunge(approve_decision)

        # Convert to HITL format
        from humancheck.models import UrgencyLevel
        universal_review = type('UniversalReview', (), {
            'task_type': review.task_type,
            'proposed_action': review.proposed_action,
            'agent_reasoning': review.agent_reasoning,
            'confidence_score': review.confidence_score,
            'urgency': UrgencyLevel(review.urgency),
            'framework': review.framework,
            'metadata': review.meta_data,
            'organization_id': review.organization_id,
            'agent_id': review.agent_id,
        })()

        decision_data = adapter.from_universal(universal_review, approve_decision)

        print(f"   ✅ Approve decision converted:")
        print(f"     - Type: {decision_data['type']}")
        assert decision_data['type'] == 'approve'

    # Test edit decision
    async with db.session() as session:
        # Edit decision with modified args
        import json
        modified_args = {
            "to": "newadmin@example.com",
            "subject": "Modified subject",
            "body": "Modified body"
        }

        edit_decision = Decision(
            review_id=review_ids[1],
            decision_type=DecisionType.MODIFY.value,
            modified_action=json.dumps(modified_args),
            notes="Changed recipient"
        )
        session.add(edit_decision)
        await session.commit()

        # Get the review with decision
        review = await session.get(Review, review_ids[1])
        session.expunge(review)
        session.expunge(edit_decision)

        # Convert to HITL format
        universal_review = type('UniversalReview', (), {
            'task_type': review.task_type,
            'proposed_action': review.proposed_action,
            'agent_reasoning': review.agent_reasoning,
            'confidence_score': review.confidence_score,
            'urgency': UrgencyLevel(review.urgency),
            'framework': review.framework,
            'metadata': review.meta_data,
            'organization_id': review.organization_id,
            'agent_id': review.agent_id,
        })()

        decision_data = adapter.from_universal(universal_review, edit_decision)

        print(f"\n   ✅ Edit decision converted:")
        print(f"     - Type: {decision_data['type']}")
        print(f"     - Args: {decision_data.get('args')}")
        assert decision_data['type'] == 'edit'
        assert decision_data['args'] == modified_args

    print("\n" + "=" * 70)
    print("✅ All tests passed!")
    print("=" * 70)
    print("\n🌐 Dashboard running at: http://localhost:8502")
    print("📋 Review IDs created: " + ", ".join(f"#{id}" for id in review_ids))
    print("\nYou can now:")
    print("  1. Open the dashboard to see the reviews")
    print("  2. Make decisions on pending reviews")
    print("  3. View the decision history")


if __name__ == "__main__":
    asyncio.run(test_hitl_integration())
