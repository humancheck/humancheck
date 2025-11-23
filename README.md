# Humancheck 🤖✋

**A universal human-in-the-loop (HITL) operations platform for AI agents**

Humancheck enables AI agents to escalate uncertain or high-stakes decisions to human reviewers for approval. It's framework-agnostic, works with any AI system, and provides a complete platform for managing human oversight at scale.

## ✨ Key Features

- **🔌 Universal Integration**: Works with any AI framework via adapter pattern
  - REST API (universal)
  - LangChain/LangGraph
  - Mastra
  - Extensible for custom frameworks
  - **Platform**: MCP (Claude Desktop native) - requires server

- **🎯 Intelligent Routing**: Route reviews to the right people based on configurable rules
  - Rule-based assignment by task type, urgency, confidence score
  - Config-based routing rules
  - Priority-based rule evaluation

- **📊 Real-time Dashboard**: Streamlit-based UI for human reviewers
  - Live review queue
  - One-click approve/reject/modify
  - Statistics and analytics

- **🔄 Flexible Workflows**: Support for both blocking and non-blocking patterns
  - Blocking: Wait for decision before proceeding
  - Non-blocking: Continue work, check back later

- **🔧 Flexible Configuration**: Simple YAML-based configuration
  - Custom routing rules
  - Default reviewers
  - Configurable thresholds

- **📈 Feedback Loop**: Continuous improvement through feedback
  - Rate decisions
  - Comment on reviews
  - Track metrics

## 🚀 Quick Start

### Installation

```bash
pip install humancheck
```

Or install from source:

```bash
git clone https://github.com/yourusername/humancheck.git
cd humancheck
poetry install
```

### Initialize Configuration

```bash
humancheck init
```

This creates a `humancheck.yaml` configuration file with sensible defaults.

### Start the Platform

```bash
humancheck start
```

This launches:
- **API Server**: http://localhost:8000
- **Dashboard**: http://localhost:8501

### Make Your First Review Request

```python
import httpx
import asyncio

async def request_review():
    async with httpx.AsyncClient() as client:
        response = await client.post(
            "http://localhost:8000/reviews",
            json={
                "task_type": "payment",
                "proposed_action": "Process payment of $5,000 to ACME Corp",
                "agent_reasoning": "Payment exceeds auto-approval limit",
                "confidence_score": 0.85,
                "urgency": "high",
                "blocking": False,
            }
        )
        review = response.json()
        print(f"Review submitted! ID: {review['id']}")

asyncio.run(request_review())
```

Open the dashboard at http://localhost:8501 to approve/reject the review!

## 📚 Usage Examples

### REST API Integration

```python
import httpx

# Non-blocking request
async with httpx.AsyncClient() as client:
    # Submit review
    response = await client.post("http://localhost:8000/reviews", json={
        "task_type": "data_deletion",
        "proposed_action": "Delete user account and all data",
        "agent_reasoning": "User requested GDPR deletion",
        "urgency": "medium",
        "blocking": False
    })
    review = response.json()
    review_id = review["id"]

    # Check status later
    status = await client.get(f"http://localhost:8000/reviews/{review_id}")

    # Get decision when ready
    if status.json()["status"] != "pending":
        decision = await client.get(f"http://localhost:8000/reviews/{review_id}/decision")
        print(decision.json())
```

### MCP Integration (Claude Desktop) - Platform Only

<Note>
MCP integration requires a server and is only available in [Humancheck Platform](https://platform.humancheck.dev).
</Note>

Add to your Claude Desktop MCP configuration:

```json
{
  "mcpServers": {
    "humancheck": {
      "command": "humancheck",
      "args": ["mcp"],
      "env": {
        "HUMANCHECK_API_URL": "https://api.humancheck.dev",
        "HUMANCHECK_API_KEY": "your-api-key-here"
      }
    }
  }
}
```

Then in Claude:

```
I need to process a $10,000 payment. Let me request human review first.

<uses request_review tool>
```

### LangChain/LangGraph Integration

```python
from langchain.agents import AgentExecutor
import httpx

# In your LangChain agent
async def execute_with_review(proposed_action, confidence):
    if confidence < 0.9:
        # Request review at interrupt point
        async with httpx.AsyncClient() as client:
            response = await client.post(
                "http://localhost:8000/reviews",
                json={
                    "task_type": "sql_execution",
                    "proposed_action": proposed_action,
                    "confidence_score": confidence,
                    "framework": "langchain",
                    "blocking": True,  # Wait for decision
                }
            )
            decision = response.json()

            if decision["decision"] == "approve":
                # Continue execution
                return execute_action(proposed_action)
            elif decision["decision"] == "modify":
                # Use modified action
                return execute_action(decision["modified_action"])
            else:
                # Rejected
                return None
```

## 🏗️ Architecture

### Core Components

1. **Adapter Pattern**: Normalizes requests from different frameworks
   - `UniversalReview`: Common format for all review requests
   - Framework-specific adapters convert to/from UniversalReview

2. **Routing Engine**: Intelligent assignment of reviews
   - Config-based routing rules
   - Priority-based evaluation
   - Supports complex conditions

3. **Dual Interface**:
   - **REST API**: Universal HTTP integration (Open Source & Platform)
   - **MCP Server**: Native Claude Desktop integration (Platform only - requires server)

4. **Dashboard**: Real-time Streamlit UI

### Data Model

```
Reviews
  ├── Decisions
  ├── Feedback
  ├── Assignments
  └── Attachments
```

## ⚙️ Configuration

Edit `humancheck.yaml`:

```yaml
api_port: 8000
streamlit_port: 8501
host: 0.0.0.0
storage: sqlite
db_path: ./humancheck.db
confidence_threshold: 0.8
require_review_for:
  - high-stakes
  - compliance
default_reviewers:
  - admin@example.com
log_level: INFO
```

Environment variables (prefix with `HUMANCHECK_`):

```bash
export HUMANCHECK_API_PORT=8000
export HUMANCHECK_DB_PATH=/var/lib/humancheck/db.sqlite
```

## 🎛️ CLI Commands

```bash
# Initialize configuration
humancheck init [--config-path PATH]

# Start API + Dashboard
humancheck start [--config PATH] [--host HOST] [--port PORT]

# Check status
humancheck status [--config PATH]

# View recent reviews
humancheck logs [--limit N] [--status-filter STATUS]
```

## 🔧 Advanced Usage

### Custom Routing Rules

Configure routing rules in `humancheck.yaml`:

```yaml
routing_rules:
  - name: "High-value payments to finance team"
    priority: 10
    conditions:
      task_type: {"operator": "=", "value": "payment"}
      metadata.amount: {"operator": ">", "value": 10000}
    assign_to: "finance@example.com"
    is_active: true
  - name: "Urgent reviews to on-call"
    priority: 20
    conditions:
      urgency: {"operator": "=", "value": "critical"}
    assign_to: "oncall@example.com"
    is_active: true
```

### Metadata Usage

You can store additional information in the `metadata` field:

```python
await client.post("http://localhost:8000/reviews", json={
    "task_type": "payment",
    "proposed_action": "Pay $5,000",
    "metadata": {
        "organization": "acme-corp",
        "agent": "payment-bot-v2",
        "amount": 5000,
        "currency": "USD"
    }
})
```

## 🧪 Testing

```bash
# Run tests
pytest

# Run with coverage
pytest --cov=humancheck tests/
```

## 📖 API Documentation

Once running, visit:
- API docs: http://localhost:8000/docs
- Alternative docs: http://localhost:8000/redoc

## 🗺️ Roadmap

### Core Features (Open Source)

- [x] Core HITL functionality
- [x] Framework adapters (REST, LangChain, Mastra)
- [x] Basic routing (config-based)
- [x] Attachments and preview
- [x] Connectors (Slack, email)
- [ ] Additional connector types
- [ ] Enhanced dashboard features
- [ ] Improved routing rule conditions
- [ ] Community contributions

### Advanced Features (Platform)

Advanced features are available in [Humancheck Platform](https://platform.humancheck.dev):

- ✅ MCP (Claude Desktop native) - requires server
- ✅ Advanced routing rules (database-backed, UI control, prioritization, fine-grained ACL)
- ✅ Dozens of built-in connectors (instant UI setup)
- ✅ No-code integrations (n8n, Zapier, Gumloop, etc.)
- ✅ Multi-user approval workflows
- ✅ Webhooks with retry logic
- ✅ Advanced analytics
- ✅ Organizations, Users, Teams
- ✅ Evals framework
- ✅ OAuth connectors
- ✅ Audit logs

<Note>
For production deployments with advanced features, check out [Humancheck Platform](https://platform.humancheck.dev) - the managed cloud service with enterprise-grade features.
</Note>

## 🤝 Contributing

Contributions are welcome! Please see [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

## 📄 License

MIT License - see [LICENSE](LICENSE) for details.

## 🙏 Acknowledgments

Built with:
- [FastAPI](https://fastapi.tiangolo.com/)
- [Streamlit](https://streamlit.io/)
- [SQLAlchemy](https://www.sqlalchemy.org/)
- [Pydantic](https://pydantic-docs.helpmanual.io/)
- [MCP](https://github.com/anthropics/mcp)

## 💬 Support

- Documentation: [docs.humancheck.dev](https://docs.humancheck.dev)
- Issues: [GitHub Issues](https://github.com/humancheck/humancheck/issues)
- Discord: [Join our community](https://discord.gg/humancheck)

---
