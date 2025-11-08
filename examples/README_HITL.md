# LangChain HITL Integration Example

This example demonstrates how to integrate LangChain's Human-in-the-Loop (HITL) middleware with humancheck's dashboard for agent oversight.

## Overview

The integration allows you to:
- Use LangChain agents with tools that require human approval
- Route approval requests to humancheck's Streamlit dashboard
- Support all three decision types: approve, edit, reject
- Track all reviews and decisions with full audit trail

## Setup

### 1. Install Dependencies

For the simple example (no OpenAI needed):
```bash
# Install humancheck
poetry install

# Or with pip
pip install -e .
```

For the full agent example (requires OpenAI):
```bash
# Install with LangChain dependencies
poetry install --with langchain

# Or with pip
pip install langchain langgraph langchain-openai langchain-core
```

### 2. Start Humancheck Services

Terminal 1 - Start the Streamlit dashboard:
```bash
streamlit run frontend/streamlit_app.py
```

The dashboard will be available at http://localhost:8501

## Running the Examples

### Simple Example (Recommended for Testing)

This example creates HITL-style reviews without requiring OpenAI:

```bash
python examples/langchain_hitl_example.py simple
```

This will:
1. Create 2 simulated tool calls (SQL delete and email send)
2. Show them in the humancheck dashboard
3. Wait for you to approve/reject/edit them
4. Display the decisions

### Full Agent Example (Requires OpenAI)

This example runs a real LangChain agent with HITL integration:

```bash
export OPENAI_API_KEY=your-key-here
python examples/langchain_hitl_example.py
```

This will:
1. Create a LangChain agent with 4 tools
2. Run 3 test queries
3. Intercept tool calls and send to humancheck
4. Wait for decisions in the dashboard
5. Apply the decisions and continue

## How It Works

### 1. HITL Adapter

The `LangChainHITLAdapter` converts HITL interrupts to humancheck reviews:

```python
from humancheck.adapters.langchain_hitl import LangChainHITLAdapter

adapter = LangChainHITLAdapter(db_session_factory)

# Create reviews from HITL interrupt
reviews = adapter.to_universal(hitl_interrupt_data)
```

### 2. Tool Approval Rules

You can configure which tools require approval:

```python
tool_approval_rules = {
    "write_file": ["approve", "edit", "reject"],  # All decisions allowed
    "execute_sql": ["approve", "reject"],          # No editing
    "send_email": ["approve", "edit", "reject"],
    "read_data": None,                             # No approval needed
}
```

### 3. Dashboard Review

When a tool call requires approval:
1. A review appears in the Streamlit dashboard
2. The reviewer can see:
   - Tool name and arguments (as JSON)
   - Agent's reasoning
   - Task type and urgency
3. Three decision options:
   - **Approve**: Execute as-is
   - **Reject**: Block with explanation
   - **Edit**: Modify tool arguments (JSON editor)

### 4. Resume Execution

After the decision:
```python
# Wait for decision (blocking)
decision = await adapter.handle_blocking(review_id, timeout=300)

# Decision format:
# {
#     "type": "approve" | "edit" | "reject",
#     "args": {...},           # Only for edit
#     "explanation": "...",    # Only for reject
#     "timestamp": "...",
#     "notes": "..."
# }
```

## Integration Patterns

### Pattern 1: Direct Integration (Used in Example)

```python
from humancheck.adapters.langchain_hitl import LangChainHITLAdapter
from humancheck.api import create_review

# Create adapter
adapter = LangChainHITLAdapter(db_session_factory)

# Build HITL request
hitl_request = {
    "action_requests": [
        {
            "name": "tool_name",
            "arguments": {"arg1": "value1"},
            "description": "Tool description"
        }
    ],
    "review_configs": [
        {
            "action_name": "tool_name",
            "allowed_decisions": ["approve", "reject"]
        }
    ],
    "thread_id": "thread-123",
}

# Convert and create reviews
reviews = adapter.to_universal(hitl_request)
async with db_session_factory() as session:
    for review in reviews:
        review_obj = await create_review(session, review)
        await session.commit()

# Wait for decisions
for review_id in review_ids:
    decision = await adapter.handle_blocking(review_id)
```

### Pattern 2: Using Helper Function

```python
from humancheck.adapters.langchain_hitl import create_hitl_interrupt_handler

# Create handler
handler = await create_hitl_interrupt_handler(db_session_factory)

# In your LangGraph code
if result.get("__interrupt__"):
    decisions = await handler(result["__interrupt__"], config)
```

## Configuration

### Routing Rules

You can configure routing rules to assign reviews to specific users or teams:

```yaml
# humancheck.yaml
routing_rules:
  - name: "SQL approvals"
    priority: 100
    conditions:
      task_type:
        operator: "contains"
        value: "execute_sql"
    assignment:
      type: "user"
      user_email: "dba@example.com"

  - name: "File operations"
    priority: 90
    conditions:
      task_type:
        operator: "contains"
        value: "write_file"
    assignment:
      type: "team"
      team_name: "dev-ops"
```

### Urgency Levels

Set urgency to prioritize reviews:

```python
hitl_request = {
    "urgency": "high",  # low, medium, high, critical
    # ...
}
```

## Troubleshooting

### Reviews not appearing in dashboard

1. Check that the Streamlit app is running
2. Verify database connection in `humancheck.yaml`
3. Check for errors in the console

### Timeout errors

Increase the timeout when waiting for decisions:

```python
decision = await adapter.handle_blocking(review_id, timeout=600)  # 10 minutes
```

### JSON validation errors in dashboard

When editing tool arguments, ensure valid JSON syntax:
- Use double quotes for strings
- No trailing commas
- Proper nesting

## Advanced Usage

### Multiple Tool Calls

Handle multiple tool calls in a single review:

```python
hitl_request = {
    "action_requests": [
        {"name": "tool1", "arguments": {...}},
        {"name": "tool2", "arguments": {...}},
    ],
    "review_configs": [
        {"action_name": "tool1", "allowed_decisions": ["approve", "reject"]},
        {"action_name": "tool2", "allowed_decisions": ["approve", "edit", "reject"]},
    ],
}

reviews = adapter.to_universal(hitl_request)  # Returns list of reviews
```

### Non-blocking Mode

For async workflows, use non-blocking mode:

```python
# Create review
review_obj = await create_review(session, review)

# Return review ID immediately
return {"review_id": review_obj.id, "status": "pending"}

# Poll later for decision
decision = await get_decision(review_id)
```

### Custom Metadata

Add custom metadata for better context:

```python
hitl_request = {
    "metadata": {
        "user_id": 123,
        "request_id": "req-456",
        "environment": "production"
    },
    # ...
}
```

## Architecture

```
┌─────────────────┐
│  LangChain      │
│  Agent          │
└────────┬────────┘
         │
         │ Tool calls
         │
         ▼
┌─────────────────┐
│  HITL Adapter   │
│  (humancheck)   │
└────────┬────────┘
         │
         │ Creates reviews
         │
         ▼
┌─────────────────┐      ┌──────────────────┐
│  Database       │◄─────┤  Streamlit       │
│  (SQLite/       │      │  Dashboard       │
│   PostgreSQL)   │      │                  │
└────────┬────────┘      └──────────────────┘
         │                        ▲
         │                        │
         │                        │ Human reviews
         │ Polls for              │ and makes
         │ decisions              │ decisions
         │                        │
         ▼                        │
┌─────────────────┐              │
│  Resume Agent   │──────────────┘
│  Execution      │
└─────────────────┘
```

## Next Steps

1. Integrate with your own LangChain agents
2. Configure routing rules for your team
3. Set up PostgreSQL for production
4. Add webhook notifications
5. Customize the dashboard UI

For more information, see the main humancheck documentation.
