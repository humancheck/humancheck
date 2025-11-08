"""Example of integrating Humancheck with LangChain/LangGraph.

This demonstrates how to use Humancheck within a LangGraph workflow
for human-in-the-loop decision making.
"""
import asyncio

import httpx


async def simulate_langchain_workflow():
    """Simulate a LangChain workflow with human review interrupt.

    In a real LangGraph implementation, you would use the interrupt()
    function to pause the workflow and wait for human input.
    """
    api_url = "http://localhost:8000"

    print("🔄 Starting LangChain workflow...")
    print("   Step 1: Analyzing user request")
    print("   Step 2: Generating SQL query")

    # Simulated LangChain state
    workflow_state = {
        "user_request": "Delete all records for user john@example.com",
        "generated_sql": "DELETE FROM users WHERE email = 'john@example.com'",
        "tables_affected": ["users", "user_sessions", "user_preferences"],
    }

    print(f"\n🔍 Generated SQL: {workflow_state['generated_sql']}")
    print("⚠️  This is a destructive operation - requesting human review")

    # Create review request via LangChain adapter
    async with httpx.AsyncClient() as client:
        review_data = {
            "task_type": "data_deletion",
            "proposed_action": workflow_state["generated_sql"],
            "agent_reasoning": (
                "User requested GDPR data deletion. This will permanently delete "
                f"data from {len(workflow_state['tables_affected'])} tables."
            ),
            "confidence_score": 0.95,
            "urgency": "medium",
            "framework": "langchain",
            "metadata": {
                "workflow_context": workflow_state,
                "interrupt_node": "sql_execution",
                "user_request": workflow_state["user_request"],
            },
            "blocking": True,  # LangChain workflows typically block at interrupts
        }

        print("\n📋 Sending review request to Humancheck...")

        try:
            # In real LangGraph, this would be wrapped in interrupt handling
            response = await client.post(
                f"{api_url}/reviews",
                json=review_data,
                timeout=600.0  # 10 minutes
            )

            result = response.json()

            if result.get("status") == "completed":
                decision = result.get("decision")

                print(f"\n✨ Received decision: {decision}")

                if decision == "approved":
                    print("\n✅ SQL execution approved by human reviewer")
                    print("   Executing query...")
                    # In real implementation, execute the SQL
                    print(f"   {workflow_state['generated_sql']}")
                    print("   ✓ Query executed successfully")

                elif decision == "rejected":
                    print("\n❌ SQL execution rejected")
                    print(f"   Reason: {result.get('notes', 'No reason provided')}")
                    print("   Aborting workflow")

                elif decision == "modified":
                    modified_sql = result.get("modified_action")
                    print(f"\n✏️ SQL modified by human reviewer")
                    print(f"   Original: {workflow_state['generated_sql']}")
                    print(f"   Modified: {modified_sql}")
                    print("   Executing modified query...")
                    # Execute modified SQL instead

                # Continue workflow after human decision
                print("\n🔄 Resuming LangChain workflow...")
                print("   Step 3: Cleanup and notification")
                print("   ✓ Workflow completed")

            else:
                print(f"\n⏰ Review timed out or pending")
                print("   Aborting workflow for safety")

        except httpx.TimeoutException:
            print("\n⏰ Timeout waiting for human decision")
            print("   Aborting workflow")


async def demonstrate_langchain_command_pattern():
    """Demonstrate using LangGraph Command pattern for resume.

    This shows how Humancheck decisions can be converted to LangGraph
    Command objects for resuming interrupted workflows.
    """
    print("\n" + "="*60)
    print("LangGraph Command Pattern Example")
    print("="*60 + "\n")

    # Simulated Command object from Humancheck decision
    command_examples = [
        {
            "command": "resume",
            "decision_type": "approve",
            "action": "approved",
            "resume_value": {
                "approved": True,
                "action": "DELETE FROM users WHERE email = 'john@example.com'"
            }
        },
        {
            "command": "resume",
            "decision_type": "modify",
            "action": "modified",
            "resume_value": {
                "approved": True,
                "action": "DELETE FROM users WHERE email = 'john@example.com' AND deleted_at IS NULL",
                "modified": True,
                "original_action": "DELETE FROM users WHERE email = 'john@example.com'"
            }
        }
    ]

    for i, cmd in enumerate(command_examples, 1):
        print(f"Example {i}: {cmd['decision_type'].upper()} decision")
        print(f"Command: {cmd['command']}")
        print(f"Resume value: {cmd['resume_value']}")
        print()


if __name__ == "__main__":
    print("🔗 LangChain + Humancheck Integration Demo\n")
    asyncio.run(simulate_langchain_workflow())
    asyncio.run(demonstrate_langchain_command_pattern())
