"""Example: LangChain with Humancheck Adapter (Self-Hosted)

This example demonstrates how to use Humancheck's LangChain adapter with a self-hosted instance.

Setup:
    1. Install dependencies: pip install langchain langgraph langchain-openai
    2. Start humancheck: humancheck start
    3. Set OPENAI_API_KEY environment variable
    4. Run this example: python examples/langchain_hitl_example.py

The example creates an agent with HumancheckLangchainAdapter that automatically
intercepts tool calls and sends them to your self-hosted Humancheck instance for review.
"""

import asyncio
import os
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))


def create_test_tools():
    """Create example tools that will require approval."""
    from langchain_core.tools import tool

    @tool
    def write_file(filename: str, content: str) -> str:
        """Write content to a file.

        Args:
            filename: Name of the file to write
            content: Content to write to the file
        """
        # In real scenario, this would write to file
        return f"File '{filename}' written successfully with {len(content)} characters"

    @tool
    def execute_sql(query: str) -> str:
        """Execute a SQL query.

        Args:
            query: SQL query to execute
        """
        # In real scenario, this would execute SQL
        return f"Query executed: {query}"

    @tool
    def send_email(to: str, subject: str, body: str) -> str:
        """Send an email.

        Args:
            to: Email recipient
            subject: Email subject
            body: Email body
        """
        # In real scenario, this would send email
        return f"Email sent to {to}"

    @tool
    def read_data(table_name: str) -> str:
        """Read data from a table (safe operation).

        Args:
            table_name: Name of the table to read from
        """
        return f"Data read from {table_name}"

    return [write_file, execute_sql, send_email, read_data]


async def setup_humancheck_integration():
    """Initialize humancheck database and get session factory."""
    from humancheck.core.config.settings import init_config
    from humancheck.core.storage.database import init_db

    config = init_config()
    db = init_db(config.get_database_url())

    # Create tables
    await db.create_tables()

    return db.session


async def create_agent_with_hitl():
    """Create a LangChain agent with HITL middleware integrated with humancheck."""
    # Import LangChain components
    try:
        from langchain_openai import ChatOpenAI
        from langgraph.checkpoint.memory import MemorySaver
        from langgraph.prebuilt import create_react_agent
    except ImportError:
        print("\n❌ LangChain dependencies not installed!")
        print("Please install them with:")
        print("  pip install langchain langgraph langchain-openai")
        sys.exit(1)

    # Check for API key
    if not os.environ.get("OPENAI_API_KEY"):
        print("\n❌ OPENAI_API_KEY environment variable not set!")
        print("Please set it with your OpenAI API key")
        sys.exit(1)

    # Initialize humancheck
    db_session_factory = await setup_humancheck_integration()

    # Create tools
    tools = create_test_tools()

    # Create the model
    model = ChatOpenAI(model="gpt-4o", temperature=0)

    # Create checkpointer for persistence
    checkpointer = MemorySaver()

    # Create the agent WITHOUT HITL middleware first
    # (We'll handle HITL manually via humancheck adapter)
    agent = create_react_agent(
        model,
        tools,
        checkpointer=checkpointer,
    )

    return agent, db_session_factory, tools


async def handle_tool_calls_with_humancheck(tool_calls, db_session_factory, config):
    """Handle tool calls through humancheck for approval.

    This function simulates what the HITL middleware would do, but routes
    through humancheck instead.

    Args:
        tool_calls: List of tool calls to review
        db_session_factory: Database session factory
        config: LangGraph config with thread_id

    Returns:
        List of decisions for each tool call
    """
    from humancheck.core.adapters.langchain import HumancheckLangchainAdapter
    
    # For self-hosted, use local API URL
    adapter = HumancheckLangchainAdapter(
        api_url="http://localhost:8000",
        api_key=None,  # No auth needed for local
        tools_requiring_approval={
            "write_file": ["approve", "edit", "reject"],
            "execute_sql": ["approve", "reject"],
            "send_email": ["approve", "edit", "reject"],
        }
    )

    # Define which tools require which approvals
    tool_approval_rules = {
        "write_file": ["approve", "edit", "reject"],
        "execute_sql": ["approve", "reject"],  # No editing allowed
        "send_email": ["approve", "edit", "reject"],
        "read_data": None,  # No approval needed
    }

    # Build HITL-style request
    action_requests = []
    review_configs = []

    for tool_call in tool_calls:
        tool_name = tool_call["name"]

        # Check if this tool requires approval
        allowed_decisions = tool_approval_rules.get(tool_name)
        if allowed_decisions is None:
            continue  # Skip tools that don't need approval

        action_requests.append({
            "name": tool_name,
            "arguments": tool_call.get("args", {}),
            "description": f"Tool execution pending approval\n\nTool: {tool_name}\nArgs: {tool_call.get('args', {})}",
        })

        review_configs.append({
            "action_name": tool_name,
            "allowed_decisions": allowed_decisions,
        })

    # If no tools need approval, return empty list
    if not action_requests:
        return []

    # Create the HITL request
    hitl_request = {
        "action_requests": action_requests,
        "review_configs": review_configs,
        "thread_id": config.get("configurable", {}).get("thread_id"),
        "config": config,
    }

    # Convert to UniversalReview(s)
    reviews = adapter.to_universal(hitl_request)

    print(f"\n📋 Created {len(reviews)} review(s) in humancheck")
    print("🌐 Check the Streamlit dashboard to approve/reject/edit")

    # Create reviews in database
    review_ids = []
    async with db_session_factory() as session:
        for review in reviews:
            review_obj = await create_review(review, session)  # Fixed argument order
            review_ids.append(review_obj.id)
            await session.commit()
            print(f"  ✓ Review #{review_obj.id}: {review.task_type}")

    # Wait for decisions
    print("\n⏳ Waiting for human decisions...")
    decisions = []
    for review_id in review_ids:
        try:
            decision = await adapter.handle_blocking(review_id, timeout=300)
            decisions.append(decision)
            print(f"  ✓ Decision received for review #{review_id}: {decision['type']}")
        except TimeoutError:
            print(f"  ⏱️  Timeout waiting for review #{review_id}")
            decisions.append({"type": "reject", "explanation": "Timeout"})

    return decisions


async def run_example():
    """Run the example agent with humancheck HITL integration."""
    print("=" * 70)
    print("LangChain HITL + Humancheck Integration Example")
    print("=" * 70)

    # Create agent
    print("\n1️⃣  Creating agent with tools...")
    agent, db_session_factory, tools = await create_agent_with_hitl()
    print("✅ Agent created")

    # Create config with thread ID
    thread_id = "example-thread-1"
    config = {"configurable": {"thread_id": thread_id}}

    # Test queries
    test_queries = [
        "Write a file called 'report.txt' with the content 'Hello World'",
        "Delete old records from the users table where created_at is older than 30 days",
        "Send an email to admin@example.com about the system status",
    ]

    print(f"\n2️⃣  Testing with {len(test_queries)} queries")
    print("📊 Open the Streamlit dashboard to review tool calls:")
    print("   streamlit run frontend/streamlit_app.py")
    print()

    for i, query in enumerate(test_queries, 1):
        print(f"\n{'='*70}")
        print(f"Query {i}: {query}")
        print('='*70)

        try:
            # Invoke agent
            result = agent.invoke(
                {"messages": [{"role": "user", "content": query}]},
                config=config
            )

            # Check if there are tool calls in the result
            if "messages" in result:
                last_message = result["messages"][-1]

                # Check if the message has tool calls
                if hasattr(last_message, "tool_calls") and last_message.tool_calls:
                    tool_calls = last_message.tool_calls

                    # Handle through humancheck
                    decisions = await handle_tool_calls_with_humancheck(
                        tool_calls,
                        db_session_factory,
                        config
                    )

                    # Process decisions
                    for decision in decisions:
                        if decision["type"] == "approve":
                            print(f"\n✅ Tool call approved")
                        elif decision["type"] == "reject":
                            print(f"\n❌ Tool call rejected: {decision.get('explanation')}")
                        elif decision["type"] == "edit":
                            print(f"\n✏️  Tool call modified: {decision.get('args')}")

            print(f"\n✅ Query {i} completed")

        except Exception as e:
            print(f"\n❌ Error: {e}")
            import traceback
            traceback.print_exc()

    print("\n" + "="*70)
    print("Example completed!")
    print("="*70)


async def simple_example():
    """Simpler example that directly creates reviews without full agent setup."""
    print("=" * 70)
    print("Simple Humancheck HITL Example (No OpenAI Required)")
    print("=" * 70)

    # Initialize humancheck
    print("\n1️⃣  Initializing humancheck...")
    from humancheck.core.config.settings import init_config
    from humancheck.core.storage.database import init_db
    from humancheck.core.adapters.langchain import HumancheckLangchainAdapter
    import httpx

    print("✅ Using Humancheck adapter")

    # Create adapter for self-hosted instance
    adapter = HumancheckLangchainAdapter(
        api_url="http://localhost:8000",
        api_key=None,  # No auth for local
        tools_requiring_approval={
            "execute_sql": {"allowed_decisions": ["approve", "reject"]},
            "send_email": True,  # All decisions allowed
        }
    )

    # Simulate a HITL interrupt with multiple tool calls
    print("\n2️⃣  Simulating HITL interrupt with tool calls...")

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
                    "subject": "Database cleanup completed",
                    "body": "Deleted old user records"
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
        "config": {}
    }

    # Use adapter to handle the interrupt (creates reviews via API)
    print("\n3️⃣  Creating reviews via Humancheck API...")
    
    # The adapter's handle_interrupt method will create reviews and wait for decisions
    decisions = await adapter.handle_interrupt([{"value": hitl_interrupt}], {})
    
    print(f"\n✅ Received {len(decisions)} decision(s)")
    for i, decision in enumerate(decisions, 1):
        print(f"\n   Decision {i}:")
        print(f"   Type: {decision['type']}")
        if decision.get('message'):
            print(f"   Message: {decision['message']}")
        if decision.get('edited_action'):
            print(f"   Edited: {decision['edited_action']}")

    print("\n" + "="*70)
    print("Example completed!")
    print("="*70)


if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1 and sys.argv[1] == "simple":
        # Run simple example without OpenAI
        asyncio.run(simple_example())
    else:
        # Run full agent example (requires OpenAI)
        asyncio.run(run_example())
