"""Basic example of using Humancheck with a simple AI agent.

This demonstrates the simplest way to integrate human-in-the-loop reviews
into an AI agent using the REST API.
"""
import asyncio

import httpx


async def main():
    """Example AI agent that requests human review for high-value payments."""
    api_url = "http://localhost:8000"

    # Example scenario: AI agent processing a payment
    payment_amount = 5000
    vendor = "ACME Corp"

    # Agent determines this needs human review
    confidence = 0.85
    threshold = 0.9  # High-stakes actions need >90% confidence

    if confidence < threshold or payment_amount > 1000:
        print(f"💰 Processing payment of ${payment_amount} to {vendor}")
        print(f"🤔 Confidence: {confidence:.1%} (threshold: {threshold:.1%})")
        print("📋 Requesting human review...\n")

        # Create review request
        async with httpx.AsyncClient() as client:
            review_data = {
                "task_type": "payment",
                "proposed_action": f"Process payment of ${payment_amount} to {vendor}",
                "agent_reasoning": (
                    f"Payment amount (${payment_amount}) exceeds auto-approval limit. "
                    f"Vendor verification confidence: {confidence:.1%}"
                ),
                "confidence_score": confidence,
                "urgency": "high",
                "framework": "custom",
                "blocking": False,  # Non-blocking: agent can continue with other work
            }

            response = await client.post(f"{api_url}/reviews", json=review_data)
            review = response.json()

            print(f"✅ Review request submitted (ID: {review['id']})")
            print(f"   Status: {review['status']}")
            print("\n⏳ Waiting for human decision...")

            # Poll for decision
            review_id = review["id"]
            max_attempts = 60
            attempt = 0

            while attempt < max_attempts:
                await asyncio.sleep(5)  # Check every 5 seconds
                attempt += 1

                # Check review status
                status_response = await client.get(f"{api_url}/reviews/{review_id}")
                review_status = status_response.json()

                if review_status["status"] != "pending":
                    # Get decision
                    decision_response = await client.get(
                        f"{api_url}/reviews/{review_id}/decision"
                    )
                    decision = decision_response.json()

                    print(f"\n✨ Decision received: {decision['decision_type']}")

                    if decision["decision_type"] == "approve":
                        print(f"   ✅ Payment approved!")
                        print(f"   💸 Processing ${payment_amount} to {vendor}...")
                        # Process the payment
                        break

                    elif decision["decision_type"] == "reject":
                        print(f"   ❌ Payment rejected")
                        print(f"   Reason: {decision.get('notes', 'No reason provided')}")
                        # Cancel the payment
                        break

                    elif decision["decision_type"] == "modify":
                        print(f"   ✏️ Payment modified")
                        print(f"   New action: {decision['modified_action']}")
                        # Process with modifications
                        break

                print(f"   Still waiting... (attempt {attempt}/{max_attempts})")

            if attempt >= max_attempts:
                print("\n⏰ Timeout waiting for decision")

            # Submit feedback
            feedback_data = {
                "rating": 5,
                "comment": "Quick and clear decision, thank you!"
            }
            await client.post(f"{api_url}/reviews/{review_id}/feedback", json=feedback_data)
            print("\n📝 Feedback submitted")

    else:
        print(f"✅ Auto-processing payment of ${payment_amount} (confidence: {confidence:.1%})")


if __name__ == "__main__":
    asyncio.run(main())
