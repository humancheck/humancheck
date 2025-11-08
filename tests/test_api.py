"""Tests for the Humancheck REST API."""
import pytest
from httpx import AsyncClient

from humancheck.api import app
from humancheck.config import init_config
from humancheck.database import init_db


@pytest.fixture
async def client():
    """Create test client with in-memory database."""
    # Use in-memory SQLite for tests
    config = init_config()
    config.db_path = ":memory:"

    db = init_db(config.get_database_url())
    await db.create_tables()

    async with AsyncClient(app=app, base_url="http://test") as ac:
        yield ac

    await db.close()


@pytest.mark.asyncio
async def test_health_check(client):
    """Test the health check endpoint."""
    response = await client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["service"] == "humancheck"


@pytest.mark.asyncio
async def test_create_review(client):
    """Test creating a review request."""
    review_data = {
        "task_type": "payment",
        "proposed_action": "Process payment of $5,000",
        "agent_reasoning": "High-value payment requires approval",
        "confidence_score": 0.85,
        "urgency": "high",
        "framework": "test",
        "blocking": False,
    }

    response = await client.post("/reviews", json=review_data)
    assert response.status_code == 201

    data = response.json()
    assert data["task_type"] == "payment"
    assert data["status"] == "pending"
    assert data["confidence_score"] == 0.85
    assert "id" in data


@pytest.mark.asyncio
async def test_list_reviews(client):
    """Test listing reviews."""
    # Create a review first
    review_data = {
        "task_type": "test",
        "proposed_action": "Test action",
        "urgency": "low",
    }
    await client.post("/reviews", json=review_data)

    # List reviews
    response = await client.get("/reviews")
    assert response.status_code == 200

    data = response.json()
    assert "reviews" in data
    assert "total" in data
    assert data["total"] >= 1


@pytest.mark.asyncio
async def test_get_review(client):
    """Test getting a specific review."""
    # Create a review
    review_data = {
        "task_type": "test",
        "proposed_action": "Test action",
        "urgency": "medium",
    }
    create_response = await client.post("/reviews", json=review_data)
    review_id = create_response.json()["id"]

    # Get the review
    response = await client.get(f"/reviews/{review_id}")
    assert response.status_code == 200

    data = response.json()
    assert data["id"] == review_id
    assert data["task_type"] == "test"


@pytest.mark.asyncio
async def test_create_decision(client):
    """Test creating a decision for a review."""
    # Create a review
    review_data = {
        "task_type": "test",
        "proposed_action": "Test action",
        "urgency": "medium",
    }
    create_response = await client.post("/reviews", json=review_data)
    review_id = create_response.json()["id"]

    # Create decision
    decision_data = {
        "decision_type": "approve",
        "notes": "Looks good!",
    }
    response = await client.post(f"/reviews/{review_id}/decide", json=decision_data)
    assert response.status_code == 200

    data = response.json()
    assert data["review_id"] == review_id
    assert data["decision_type"] == "approve"
    assert data["notes"] == "Looks good!"


@pytest.mark.asyncio
async def test_submit_feedback(client):
    """Test submitting feedback on a review."""
    # Create a review
    review_data = {
        "task_type": "test",
        "proposed_action": "Test action",
        "urgency": "medium",
    }
    create_response = await client.post("/reviews", json=review_data)
    review_id = create_response.json()["id"]

    # Submit feedback
    feedback_data = {
        "rating": 5,
        "comment": "Great response time!",
    }
    response = await client.post(f"/reviews/{review_id}/feedback", json=feedback_data)
    assert response.status_code == 201

    data = response.json()
    assert data["review_id"] == review_id
    assert data["rating"] == 5


@pytest.mark.asyncio
async def test_get_statistics(client):
    """Test getting review statistics."""
    # Create some reviews
    for i in range(3):
        await client.post("/reviews", json={
            "task_type": "test",
            "proposed_action": f"Test action {i}",
            "urgency": "medium",
            "confidence_score": 0.8 + (i * 0.05),
        })

    # Get statistics
    response = await client.get("/stats")
    assert response.status_code == 200

    data = response.json()
    assert data["total_reviews"] >= 3
    assert "avg_confidence_score" in data
    assert "task_type_breakdown" in data


@pytest.mark.asyncio
async def test_filter_reviews_by_status(client):
    """Test filtering reviews by status."""
    # Create and approve a review
    review_data = {
        "task_type": "test",
        "proposed_action": "Test action",
        "urgency": "medium",
    }
    create_response = await client.post("/reviews", json=review_data)
    review_id = create_response.json()["id"]

    await client.post(f"/reviews/{review_id}/decide", json={
        "decision_type": "approve"
    })

    # Filter by approved status
    response = await client.get("/reviews?status=approved")
    assert response.status_code == 200

    data = response.json()
    assert all(r["status"] == "approved" for r in data["reviews"])
