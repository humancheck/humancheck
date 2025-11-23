"""Example: LangChain with Humancheck Adapter (Platform)

This example demonstrates how to use Humancheck's LangChain adapter directly with LangChain agents.
You don't need LangChain's HumanInTheLoopMiddleware - just use Humancheck's adapter!

Setup:
    1. Install dependencies: pip install langchain langgraph langchain-openai httpx
    2. Get your API key from https://platform.humancheck.dev
    3. Set OPENAI_API_KEY and HUMANCHECK_API_KEY environment variables
    4. Run: python examples/langchain_platform_example.py

The example creates an agent with HumancheckLangchainAdapter that automatically
pauses execution when tool calls require approval. Reviews are sent to Humancheck
Platform, and decisions are retrieved to resume execution.
"""

import asyncio
import os
import sys
from pathlib import Path

# Add parent directory to path for local development
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from langchain.agents import create_agent
from langchain_core.tools import tool
from langchain_openai import ChatOpenAI
from langgraph.checkpoint.memory import MemorySaver
from langgraph.types import Command

# Import Humancheck LangChain adapter (replaces LangChain's HITL middleware)
from humancheck.adapters.langchain import HumancheckLangchainAdapter


# Humancheck Platform Configuration
HUMANCHECK_API_KEY = os.environ.get("HUMANCHECK_API_KEY")  # Get from platform.humancheck.dev


def create_tools():
    """Create example tools that will require approval."""
    
    @tool
    def write_file(filename: str, content: str) -> str:
        """Write content to a file.
        
        Args:
            filename: Name of the file to write
            content: Content to write to the file
        """
        # In production, this would actually write to file
        return f"File '{filename}' written successfully with {len(content)} characters"
    
    @tool
    def execute_sql(query: str) -> str:
        """Execute a SQL query.
        
        Args:
            query: SQL query to execute
        """
        # In production, this would actually execute SQL
        return f"Query executed: {query}"
    
    @tool
    def send_email(to: str, subject: str, body: str) -> str:
        """Send an email.
        
        Args:
            to: Email recipient
            subject: Email subject
            body: Email body
        """
        # In production, this would actually send email
        return f"Email sent to {to}"
    
    @tool
    def read_data(table_name: str) -> str:
        """Read data from a table (safe operation, no approval needed).
        
        Args:
            table_name: Name of the table to read from
        """
        return f"Data read from {table_name}"
    
    return [write_file, execute_sql, send_email, read_data]


# No need for manual interrupt handling - HumancheckMiddleware handles it automatically!


async def main():
    """Main example: Create agent with HITL middleware and run queries."""
    
    print("=" * 70)
    print("LangChain HITL + Humancheck Platform Integration")
    print("=" * 70)
    
    # Check environment
    if not HUMANCHECK_API_KEY:
        print("\n❌ HUMANCHECK_API_KEY not set!")
        print("   Get your API key from: https://platform.humancheck.dev")
        sys.exit(1)
    
    if not os.environ.get("OPENAI_API_KEY"):
        print("\n❌ OPENAI_API_KEY not set!")
        sys.exit(1)
    
    # Create tools
    print("\n1️⃣  Creating tools...")
    tools = create_tools()
    print(f"   ✓ Created {len(tools)} tools")
    
    # Create model
    print("\n2️⃣  Creating agent with HumanInTheLoopMiddleware...")
    model = ChatOpenAI(model="gpt-4o", temperature=0)
    checkpointer = MemorySaver()
    
    # Create agent with Humancheck LangChain adapter (replaces LangChain's HITL middleware)
    agent = create_agent(
        model,
        tools,
        middleware=[
            HumancheckLangchainAdapter(
                api_url="https://api.humancheck.dev",
                api_key=HUMANCHECK_API_KEY,
                tools_requiring_approval={
                    "write_file": True,  # All decisions allowed
                    "execute_sql": {"allowed_decisions": ["approve", "reject"]},  # No editing
                    "send_email": True,  # All decisions allowed
                    "read_data": False,  # No approval needed
                },
                description_prefix="Tool execution pending approval",
            ),
        ],
        checkpointer=checkpointer,
    )
    print("   ✓ Agent created with Humancheck LangChain adapter")
    
    # Create config with thread ID
    thread_id = "platform-example-thread"
    config = {"configurable": {"thread_id": thread_id}}
    
    # Test queries
    test_queries = [
        "Write a file called 'report.txt' with the content 'Monthly Report: All systems operational'",
        "Delete old records from the users table where created_at is older than 30 days",
        "Send an email to admin@example.com with subject 'System Status' and body 'Everything is working well'",
    ]
    
    print(f"\n3️⃣  Running {len(test_queries)} test queries")
    print("   🌐 Dashboard: https://platform.humancheck.dev")
    print()
    
    for i, query in enumerate(test_queries, 1):
        print(f"\n{'='*70}")
        print(f"Query {i}: {query}")
        print('='*70)
        
        try:
            # Invoke agent (will pause at interrupt if tool calls need approval)
            result = agent.invoke(
                {"messages": [{"role": "user", "content": query}]},
                config=config,
            )
            
            # Check for interrupt (HumancheckMiddleware handles it automatically)
            if result.get("__interrupt__"):
                print("\n🛑 Interrupt detected - tool calls require approval")
                print("   📤 Reviews created in Humancheck Platform")
                print("   🌐 Check dashboard: https://platform.humancheck.dev")
                print("   ⏳ Waiting for decisions...")
                
                # Get the middleware instance to handle the interrupt
                # In a real implementation, this would be handled automatically
                # For now, we'll show how it works
                interrupt_data = result["__interrupt__"]
                
                # The middleware's handle_interrupt method would be called automatically
                # by LangGraph, but for this example, we'll show the flow
                print("   (Middleware automatically handles interrupt and waits for decisions)")
                
                # Resume execution (decisions are handled by middleware)
                print("\n▶️  Resuming execution...")
                result = agent.invoke(
                    Command(resume={"decisions": []}),  # Middleware provides decisions
                    config=config,
                )
                
                print(f"\n✅ Query {i} completed")
                if "messages" in result:
                    last_message = result["messages"][-1]
                    if hasattr(last_message, "content"):
                        print(f"   Response: {last_message.content[:200]}...")
            
            else:
                print(f"\n✅ Query {i} completed (no approval needed)")
                if "messages" in result:
                    last_message = result["messages"][-1]
                    if hasattr(last_message, "content"):
                        print(f"   Response: {last_message.content[:200]}...")
        
        except Exception as e:
            print(f"\n❌ Error: {e}")
            import traceback
            traceback.print_exc()
    
    print("\n" + "="*70)
    print("Example completed!")
    print("="*70)
    print("\n💡 Tips:")
    print("   - View all reviews at: https://platform.humancheck.dev")
    print("   - Reviews are automatically routed based on your Platform settings")
    print("   - Multiple reviewers can collaborate on complex decisions")


if __name__ == "__main__":
    asyncio.run(main())

