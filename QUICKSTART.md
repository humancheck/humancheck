# Humancheck Quick Start Guide

Get up and running with Humancheck in 5 minutes!

## Installation

```bash
# Install with pip
pip install humancheck

# Or install from source
git clone https://github.com/yourusername/humancheck.git
cd humancheck
poetry install
```

## 1. Initialize Configuration

```bash
humancheck init
```

This creates `humancheck.yaml` with default settings. You can customize:
- Database path
- API/Dashboard ports
- Review thresholds
- Default reviewers

## 2. Start the Platform

```bash
humancheck start
```

This launches:
- **API Server**: http://localhost:8000
- **Dashboard**: http://localhost:8501

## 3. Create Your First Review

### Option A: Using Python

Create `test_review.py`:

```python
import httpx
import asyncio

async def main():
    async with httpx.AsyncClient() as client:
        # Create a review request
        response = await client.post(
            "http://localhost:8000/reviews",
            json={
                "task_type": "payment",
                "proposed_action": "Process payment of $5,000 to ACME Corp",
                "agent_reasoning": "High-value payment requires human approval",
                "confidence_score": 0.85,
                "urgency": "high",
            }
        )
        review = response.json()
        print(f"✅ Review created! ID: {review['id']}")
        print(f"📊 View in dashboard: http://localhost:8501")

asyncio.run(main())
```

Run it:
```bash
python test_review.py
```

### Option B: Using cURL

```bash
curl -X POST http://localhost:8000/reviews \
  -H "Content-Type: application/json" \
  -d '{
    "task_type": "payment",
    "proposed_action": "Process payment of $5,000 to ACME Corp",
    "agent_reasoning": "High-value payment requires approval",
    "confidence_score": 0.85,
    "urgency": "high"
  }'
```

## 4. Review and Approve

1. Open the dashboard: http://localhost:8501
2. You'll see your review in the queue
3. Click to expand the review
4. Choose:
   - ✅ **Approve**: Accept the proposed action
   - ❌ **Reject**: Deny the action
   - ✏️ **Modify**: Change the action before approving

## 5. Check the Decision (in code)

```python
import httpx
import asyncio

async def check_decision(review_id):
    async with httpx.AsyncClient() as client:
        # Check review status
        response = await client.get(f"http://localhost:8000/reviews/{review_id}")
        review = response.json()

        if review["status"] != "pending":
            # Get the decision
            decision_response = await client.get(
                f"http://localhost:8000/reviews/{review_id}/decision"
            )
            decision = decision_response.json()

            print(f"Decision: {decision['decision_type']}")
            if decision["decision_type"] == "approve":
                print("✅ Action was approved!")
            elif decision["decision_type"] == "reject":
                print(f"❌ Action was rejected: {decision.get('notes')}")
            elif decision["decision_type"] == "modify":
                print(f"✏️ Action was modified: {decision['modified_action']}")
        else:
            print("⏳ Still waiting for review...")

# Replace 1 with your review ID
asyncio.run(check_decision(1))
```

## Next Steps

### Set Up Organizations and Users

```python
import httpx
import asyncio

async def setup():
    async with httpx.AsyncClient() as client:
        # Create organization
        org = await client.post("http://localhost:8000/organizations", json={
            "name": "My Company"
        })
        org_id = org.json()["id"]

        # Create reviewer user
        user = await client.post("http://localhost:8000/users", json={
            "email": "reviewer@mycompany.com",
            "name": "Alice Smith",
            "role": "reviewer",
            "organization_id": org_id
        })
        print(f"✅ Created organization and user")

asyncio.run(setup())
```

### Create Routing Rules

```python
async def create_routing_rule(org_id, user_id):
    async with httpx.AsyncClient() as client:
        # Route high-value payments to specific reviewer
        rule = await client.post("http://localhost:8000/routing-rules", json={
            "name": "High-value payments",
            "organization_id": org_id,
            "priority": 10,
            "conditions": {
                "task_type": {"operator": "=", "value": "payment"},
                "confidence_score": {"operator": "<", "value": 0.9}
            },
            "assign_to_user_id": user_id,
            "is_active": True
        })
        print(f"✅ Created routing rule")
```

### Use with Claude Desktop (MCP)

1. Add to your Claude Desktop config (`~/Library/Application Support/Claude/claude_desktop_config.json`):

```json
{
  "mcpServers": {
    "humancheck": {
      "command": "humancheck",
      "args": ["mcp"]
    }
  }
}
```

2. Restart Claude Desktop

3. In Claude, you can now use:
```
I need to process a high-value payment. Let me request human review.
```

Claude will use the `request_review` tool automatically!

## Common Use Cases

### 1. Payment Approval Workflow

```python
async def payment_workflow(amount, vendor):
    if amount > 1000:
        # Request review for large payments
        review = await create_review(
            task_type="payment",
            proposed_action=f"Pay ${amount} to {vendor}",
            urgency="high" if amount > 5000 else "medium"
        )
        decision = await wait_for_decision(review["id"])
        if decision["decision_type"] == "approve":
            process_payment(amount, vendor)
```

### 2. Data Deletion (GDPR)

```python
async def delete_user_data(user_email):
    # Always require review for data deletion
    review = await create_review(
        task_type="data_deletion",
        proposed_action=f"Delete all data for {user_email}",
        agent_reasoning="User requested GDPR deletion",
        urgency="medium"
    )
    decision = await wait_for_decision(review["id"])
    if decision["decision_type"] == "approve":
        delete_user(user_email)
```

### 3. Content Moderation

```python
async def moderate_content(content, confidence):
    if confidence < 0.8:
        # Borderline content needs human review
        review = await create_review(
            task_type="content_moderation",
            proposed_action=f"Flag content as inappropriate",
            agent_reasoning="Low confidence in moderation decision",
            confidence_score=confidence,
            urgency="high"
        )
```

## CLI Commands Reference

```bash
# Initialize config
humancheck init

# Start API + Dashboard
humancheck start

# Start only API (no dashboard)
humancheck start --no-dashboard

# Run as MCP server
humancheck mcp

# Check system status
humancheck status

# View recent reviews
humancheck logs --limit 20

# View only pending reviews
humancheck logs --status-filter pending
```

## Troubleshooting

### Port Already in Use

```bash
# Use different ports
humancheck start --port 8001
```

Or edit `humancheck.yaml`:
```yaml
api_port: 8001
streamlit_port: 8502
```

### Database Issues

```bash
# Check database connection
humancheck status

# Reset database (WARNING: deletes all data)
rm humancheck.db
humancheck start
```

### Can't Access Dashboard

1. Check if it's running:
   ```bash
   ps aux | grep streamlit
   ```

2. Check logs:
   ```bash
   humancheck logs
   ```

3. Try accessing directly:
   ```bash
   streamlit run frontend/streamlit_app.py
   ```

## More Examples

Check the `examples/` directory:
- `basic_agent.py` - Simple agent integration
- `langchain_integration.py` - LangChain/LangGraph example

## Documentation

- Full documentation: https://docs.humancheck.dev
- API reference: http://localhost:8000/docs
- GitHub: https://github.com/yourusername/humancheck

## Support

- Issues: https://github.com/yourusername/humancheck/issues
- Discord: https://discord.gg/humancheck
- Email: hello@humancheck.dev

---

Happy reviewing! 🎉
