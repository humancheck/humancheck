# Humancheck Connectors System

The Connectors system allows Humancheck to send review notifications through various communication channels (Slack, email, webhooks, etc.) and route reviews to the appropriate reviewers automatically.

## Architecture

```
Review Created
    ↓
ConnectorManager.send_review_notification()
    ↓
RoutingEngine.route_review()
    ↓
Evaluate ConnectorRoutingRules
    ↓
Send via matching Connectors (Slack, Email, etc.)
    ↓
Log to NotificationLog
```

## Core Components

### 1. Base Connector (`connectors/base.py`)
Abstract base class that all connectors inherit from:
- `send_review_notification()` - Send notification about pending review
- `send_decision_notification()` - Send notification about completed decision
- `update_notification()` - Update existing notification (for interactive channels)
- `test_connection()` - Test connector configuration

### 2. Slack Connector (`connectors/slack.py`)
Sends rich formatted messages to Slack channels using Slack Block Kit:
- Supports channels and DMs
- Rich formatting with urgency indicators
- Dashboard links for easy navigation
- Can be extended to support interactive buttons

### 3. Routing Engine (`routing.py`)
Evaluates routing rules to determine which connectors should receive notifications:
- Priority-based rule evaluation
- Supports multiple matching rules
- Flexible condition matching:
  - Task type (e.g., `tool_call_execute_sql`)
  - Urgency levels
  - Framework
  - Confidence score thresholds
  - Custom metadata fields

### 4. Connector Manager (`connector_manager.py`)
Central orchestration service:
- Manages connector instances
- Coordinates notification sending
- Tracks delivery status
- Provides CRUD operations for connectors

### 5. Database Models (`connector_models.py`)

#### ConnectorConfig
Stores connector configurations:
```python
{
    "id": 1,
    "connector_type": "slack",
    "name": "Team Slack",
    "config_data": {
        "bot_token": "xoxb-...",
        "signing_secret": "..."
    },
    "enabled": true,
    "organization_id": null
}
```

#### ConnectorRoutingRule
Defines routing logic:
```python
{
    "id": 1,
    "connector_id": 1,
    "name": "SQL Reviews to DB Team",
    "priority": 100,
    "conditions": {
        "task_type": "tool_call_execute_sql",
        "urgency": ["high", "critical"]
    },
    "recipients": ["#database-team"],
    "enabled": true
}
```

#### NotificationLog
Tracks notification delivery:
```python
{
    "id": 1,
    "review_id": 123,
    "connector_id": 1,
    "status": "sent",  # sent, failed, delivered, read
    "recipient": "#database-team",
    "message_id": "1234567890.123456",  # External ID
    "sent_at": "2024-01-01T12:00:00Z"
}
```

## Usage

### Setting Up a Slack Connector

```python
from humancheck.connector_manager import ConnectorManager
from humancheck.database import init_db

async with db.session() as session:
    manager = ConnectorManager(session)

    # Create Slack connector
    connector = await manager.create_connector(
        connector_type='slack',
        name='Team Slack Workspace',
        config_data={
            'bot_token': 'xoxb-your-bot-token-here'
        }
    )
```

### Creating Routing Rules

```python
# Route SQL reviews to #database-team
await manager.routing_engine.create_rule(
    connector_id=connector.id,
    name="SQL Reviews to DB Team",
    conditions={
        "task_type": "tool_call_execute_sql",
        "urgency": ["high", "critical"]
    },
    recipients=["#database-team"],
    priority=100
)

# Route all critical reviews to #urgent-reviews
await manager.routing_engine.create_rule(
    connector_id=connector.id,
    name="Critical Reviews",
    conditions={
        "urgency": "critical"
    },
    recipients=["#urgent-reviews", "@oncall"],
    priority=200  # Higher priority
)

# Route low confidence reviews
await manager.routing_engine.create_rule(
    connector_id=connector.id,
    name="Low Confidence Reviews",
    conditions={
        "max_confidence": 0.7
    },
    recipients=["#review-queue"],
    priority=50
)
```

### Sending Notifications

```python
# When a review is created
async with db.session() as session:
    manager = ConnectorManager(session)

    # Send review notification
    logs = await manager.send_review_notification(
        review,
        additional_context={
            "dashboard_url": f"http://localhost:8502?review_id={review.id}"
        }
    )

    print(f"Sent {len(logs)} notifications")
```

```python
# When a decision is made
async with db.session() as session:
    manager = ConnectorManager(session)

    # Send decision notification
    logs = await manager.send_decision_notification(review, decision)

    print(f"Sent {len(logs)} decision notifications")
```

### Integration with Existing Code

Add to your review creation endpoint:

```python
@app.post("/reviews")
async def create_review(review_data: dict):
    # Create review
    review = await save_review(review_data)

    # Send notifications
    async with db.session() as session:
        manager = ConnectorManager(session)
        await manager.send_review_notification(review)

    return review
```

Add to your decision creation:

```python
async def create_decision(review_id, decision_type, ...):
    # Create decision
    decision = await save_decision(...)

    # Send notifications
    async with db.session() as session:
        manager = ConnectorManager(session)
        await manager.send_decision_notification(review, decision)

    return decision
```

## Routing Rule Conditions

Routing rules support flexible condition matching:

### Task Type Matching
```python
conditions = {
    "task_type": "tool_call_execute_sql"  # Single type
}

conditions = {
    "task_type": ["tool_call_execute_sql", "tool_call_send_email"]  # Multiple
}
```

### Urgency Matching
```python
conditions = {
    "urgency": "critical"  # Single level
}

conditions = {
    "urgency": ["high", "critical"]  # Multiple levels
}
```

### Confidence Score Thresholds
```python
conditions = {
    "min_confidence": 0.5,  # At least 50%
    "max_confidence": 0.9   # At most 90%
}
```

### Custom Metadata
```python
conditions = {
    "metadata": {
        "environment": "production",
        "severity": ["medium", "high"]
    }
}
```

### Catch-All Rules
```python
conditions = {}  # Matches everything
```

## Available Connectors

### Slack (`slack`)
**Config:**
```python
{
    "bot_token": "xoxb-...",           # Required: Bot User OAuth Token
    "app_token": "xapp-..." (optional), # For Socket Mode
    "signing_secret": "..." (optional)  # For webhook verification
}
```

**Recipients:** Channel names/IDs (`#reviews`, `C01234567`), User IDs (`@user`, `U01234567`)

### Future Connectors

- **Email** - SMTP-based email notifications
- **Webhook** - Generic HTTP POST to any endpoint
- **Discord** - Discord channel notifications
- **Microsoft Teams** - Teams adaptive cards
- **Telegram** - Telegram bot notifications
- **PagerDuty** - For critical/urgent reviews
- **SMS/Twilio** - For critical alerts

## Creating Custom Connectors

Extend the `ReviewConnector` base class:

```python
from humancheck.connectors.base import ReviewConnector

class CustomConnector(ReviewConnector):
    def _get_connector_type(self) -> str:
        return "custom"

    async def send_review_notification(self, review, recipients, context=None):
        # Your implementation
        return {
            "success": True,
            "message_id": "external_id"
        }

    async def send_decision_notification(self, review, decision, recipients):
        # Your implementation
        return {"success": True}

    async def test_connection(self):
        # Test configuration
        return {"success": True, "message": "Connected!"}
```

Register in `ConnectorManager.CONNECTOR_TYPES`:
```python
CONNECTOR_TYPES = {
    'slack': SlackConnector,
    'custom': CustomConnector,
    # ...
}
```

## Setting Up Slack Bot

1. **Create Slack App** at https://api.slack.com/apps
2. **Add Bot Token Scopes**:
   - `chat:write` - Post messages
   - `chat:write.public` - Post to public channels without joining
3. **Install to Workspace** - Get Bot User OAuth Token (`xoxb-...`)
4. **Invite Bot to Channels**: `/invite @your-bot-name` in each channel
5. **Use Token** in connector config

## Example Integration Script

See `examples/connector_integration.py` for a complete working example showing:
- Creating connectors
- Setting up routing rules
- Sending notifications
- Complete integration flow

Run it with:
```bash
poetry run python examples/connector_integration.py
```

## Database Schema

The connector system adds three new tables:

- `connector_configs` - Connector configurations
- `connector_routing_rules` - Routing rules
- `notification_logs` - Notification delivery tracking

Tables are created automatically when you run:
```bash
poetry run python init_connector_tables.py
```

## Monitoring and Debugging

### Check Notification Status
```python
# Get all notifications for a review
logs = await session.execute(
    select(NotificationLog).where(NotificationLog.review_id == review_id)
)
for log in logs.scalars():
    print(f"{log.recipient}: {log.status}")
```

### Test Connector
```python
result = await manager.test_connector(connector_id)
if result['success']:
    print(f"✅ Connected: {result['message']}")
else:
    print(f"❌ Failed: {result['message']}")
```

### View Active Rules
```python
rules = await manager.routing_engine.get_rules_for_connector(connector_id)
for rule in rules:
    print(f"{rule.name} (priority={rule.priority})")
```

## Best Practices

1. **Use Priority Wisely** - Higher priority rules (e.g., critical alerts) should have higher values
2. **Test Connectors** - Always test after creating/updating connector configs
3. **Monitor Logs** - Check `notification_logs` table for delivery status
4. **Catch-All Rules** - Create low-priority catch-all rules to ensure all reviews are routed
5. **Organization Scoping** - Use `organization_id` for multi-tenant deployments
6. **Deduplicate Recipients** - Routing engine automatically deduplicates recipients per connector

## Troubleshooting

**Notifications not sending?**
- Check connector is `enabled = true`
- Verify routing rules match your review
- Test connector connection
- Check `notification_logs` for errors

**Slack messages failing?**
- Verify bot token is correct
- Ensure bot is invited to channels
- Check bot has required scopes
- Test with `await connector.test_connection()`

**Wrong reviews being routed?**
- Review rule priorities (higher = evaluated first)
- Check condition logic
- Use `routing_engine._evaluate_rule()` to debug

## LangChain/LangGraph Integration

The connector system integrates seamlessly with LangChain agents. When a decision is made in Slack (or other channels), you can resume the LangGraph agent:

```python
# After receiving decision from Slack
decision = await get_decision(review_id)

# Resume LangGraph agent
agent.invoke(
    Command(
        resume={
            "decisions": [{
                "type": decision.decision_type,
                "action": decision.modified_action,
                "feedback": decision.notes
            }]
        }
    ),
    config={"configurable": {"thread_id": review.meta_data["thread_id"]}}
)
```

## Future Enhancements

- [ ] Interactive Slack buttons (approve/reject in-channel)
- [ ] Email connector with HTML templates
- [ ] Webhook connector with custom payloads
- [ ] Notification digests (batch notifications)
- [ ] SLA tracking and escalation
- [ ] A/B testing different notification strategies
- [ ] Analytics dashboard for notification effectiveness
