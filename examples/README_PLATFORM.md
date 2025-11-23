# LangChain HITL with Humancheck Platform Example

This example demonstrates how to integrate LangChain's built-in `HumanInTheLoopMiddleware` with **Humancheck Platform** (cloud) for human oversight of agent tool calls.

## Overview

When using Humancheck Platform, you don't need to self-host anything. Reviews are managed in the cloud, and you can access them via the dashboard at [platform.humancheck.dev](https://platform.humancheck.dev).

## Setup

### 1. Get Your API Key

1. Sign up at [platform.humancheck.dev](https://platform.humancheck.dev)
2. Navigate to your organization settings
3. Generate an API key
4. Copy the key (you'll only see it once)

### 2. Install Dependencies

```bash
pip install langchain langgraph langchain-openai httpx
```

### 3. Set Environment Variables

```bash
export OPENAI_API_KEY="your-openai-key"
export HUMANCHECK_API_KEY="your-humancheck-platform-key"
```

### 4. Run the Example

```bash
python examples/langchain_platform_example.py
```

## How It Works

### 1. Agent Setup

The agent is created with `HumanInTheLoopMiddleware`:

```python
from langchain.agents import create_agent
from langchain.agents.middleware import HumanInTheLoopMiddleware

agent = create_agent(
    model,
    tools,
    middleware=[
        HumanInTheLoopMiddleware(
            interrupt_on={
                "write_file": True,  # All decisions allowed
                "execute_sql": {"allowed_decisions": ["approve", "reject"]},
                "send_email": True,
                "read_data": False,  # No approval needed
            },
        ),
    ],
    checkpointer=MemorySaver(),
)
```

### 2. Execution Flow

1. **Agent runs** until it needs to call a tool that requires approval
2. **Middleware raises interrupt** with tool call details
3. **Interrupt handler** creates reviews in Humancheck Platform via API
4. **Human reviews** the tool calls in the Platform dashboard
5. **Decisions are retrieved** from Platform via API
6. **Agent resumes** execution with `Command(resume={"decisions": [...]})`

### 3. Review Creation

When an interrupt occurs, reviews are created in Platform:

```python
# HITL interrupt contains:
{
    "action_requests": [
        {
            "name": "execute_sql",
            "arguments": {"query": "DELETE FROM users WHERE ..."},
            "description": "Tool execution pending approval..."
        }
    ],
    "review_configs": [
        {
            "action_name": "execute_sql",
            "allowed_decisions": ["approve", "reject"]
        }
    ]
}

# Converted to Platform review:
POST https://api.humancheck.dev/reviews
{
    "task_type": "tool_call_execute_sql",
    "proposed_action": "Tool: execute_sql\nArguments: {...}",
    "agent_reasoning": "Tool execution pending approval...",
    "metadata": {
        "tool_name": "execute_sql",
        "tool_arguments": {...},
        "allowed_decisions": ["approve", "reject"]
    }
}
```

### 4. Decision Retrieval

Decisions are polled from Platform and converted to LangChain format:

```python
# Platform decision:
{
    "decision_type": "approve" | "reject" | "modify",
    "notes": "...",
    "modified_action": "..."  # Only for modify
}

# Converted to LangChain HITL format:
{
    "type": "approve"
}
# or
{
    "type": "reject",
    "message": "..."
}
# or
{
    "type": "edit",
    "edited_action": {
        "name": "tool_name",
        "args": {...}
    }
}
```

### 5. Resume Execution

```python
from langgraph.types import Command

agent.invoke(
    Command(resume={"decisions": [decision1, decision2, ...]}),
    config=config
)
```

## Platform Features

When using Humancheck Platform, you get:

- ✅ **Built-in routing** - Automatic assignment to reviewers
- ✅ **Multi-user workflows** - Sequential/parallel approvals
- ✅ **Webhooks** - Real-time notifications
- ✅ **Audit logs** - Complete history
- ✅ **Dashboard** - Visual review interface
- ✅ **No infrastructure** - Fully managed

## Example Output

```
======================================================================
LangChain HITL + Humancheck Platform Integration
======================================================================

1️⃣  Creating tools...
   ✓ Created 4 tools

2️⃣  Creating agent with HumanInTheLoopMiddleware...
   ✓ Agent created with HITL middleware

3️⃣  Running 3 test queries
   🌐 Dashboard: https://platform.humancheck.dev

======================================================================
Query 1: Write a file called 'report.txt'...
======================================================================

🛑 Interrupt detected - tool calls require approval

📤 Creating reviews in Humancheck Platform...
  ✓ Review #123 created in Platform: write_file

⏳ Waiting for decisions from Platform...
   Review IDs: [123]
  ✓ Decision received for Review #123: approve

▶️  Resuming execution with decisions...

✅ Query 1 completed
```

## Differences from Self-Hosted

| Feature | Self-Hosted | Platform |
|---------|-------------|----------|
| Setup | Install & configure | Just API key |
| Dashboard | Local (localhost:8501) | Cloud (platform.humancheck.dev) |
| Routing | Config-based (YAML) | UI-based with ACL |
| Multi-user | Manual | Built-in workflows |
| Webhooks | Basic | Advanced with retry |
| Maintenance | You manage | Fully managed |

## Next Steps

- View reviews at [platform.humancheck.dev](https://platform.humancheck.dev)
- Configure routing rules in Platform dashboard
- Set up webhooks for automation
- Explore multi-user approval workflows

