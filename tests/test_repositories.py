"""Tests for repository pattern implementations."""
import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from humancheck.core.models import (
    Review,
    Decision,
    Feedback,
    ReviewAssignment,
    Attachment,
    ReviewStatus,
    DecisionType,
    UrgencyLevel,
    ContentCategory,
)
from humancheck.core.storage.database import Database, init_db
from humancheck.core.storage.repositories import (
    ReviewRepository,
    DecisionRepository,
    FeedbackRepository,
    AssignmentRepository,
    AttachmentRepository,
)
from humancheck.core.config.settings import init_config


@pytest.fixture
async def db():
    """Create test database."""
    config = init_config()
    config.db_path = ":memory:"
    db = init_db(config.get_database_url())
    await db.create_tables()
    yield db
    await db.close()


@pytest.fixture
async def session(db: Database):
    """Create test session."""
    async with db.session() as session:
        yield session


@pytest.fixture
async def review_repo(session: AsyncSession):
    """Create review repository."""
    return ReviewRepository(session)


@pytest.fixture
async def decision_repo(session: AsyncSession):
    """Create decision repository."""
    return DecisionRepository(session)


@pytest.fixture
async def feedback_repo(session: AsyncSession):
    """Create feedback repository."""
    return FeedbackRepository(session)


@pytest.fixture
async def assignment_repo(session: AsyncSession):
    """Create assignment repository."""
    return AssignmentRepository(session)


@pytest.fixture
async def attachment_repo(session: AsyncSession):
    """Create attachment repository."""
    return AttachmentRepository(session)


@pytest.mark.asyncio
async def test_review_repository_create(review_repo: ReviewRepository):
    """Test creating a review."""
    review = Review(
        task_type="test",
        proposed_action="Test action",
        urgency=UrgencyLevel.MEDIUM.value,
        status=ReviewStatus.PENDING.value,
    )
    
    created = await review_repo.create(review)
    assert created.id is not None
    assert created.task_type == "test"
    assert created.status == ReviewStatus.PENDING.value


@pytest.mark.asyncio
async def test_review_repository_get(review_repo: ReviewRepository):
    """Test getting a review by ID."""
    review = Review(
        task_type="test",
        proposed_action="Test action",
        urgency=UrgencyLevel.MEDIUM.value,
        status=ReviewStatus.PENDING.value,
    )
    created = await review_repo.create(review)
    
    retrieved = await review_repo.get(created.id)
    assert retrieved is not None
    assert retrieved.id == created.id
    assert retrieved.task_type == "test"


@pytest.mark.asyncio
async def test_review_repository_update(review_repo: ReviewRepository):
    """Test updating a review."""
    review = Review(
        task_type="test",
        proposed_action="Test action",
        urgency=UrgencyLevel.MEDIUM.value,
        status=ReviewStatus.PENDING.value,
    )
    created = await review_repo.create(review)
    
    updated = await review_repo.update(created.id, status=ReviewStatus.APPROVED.value)
    assert updated is not None
    assert updated.status == ReviewStatus.APPROVED.value


@pytest.mark.asyncio
async def test_review_repository_list(review_repo: ReviewRepository):
    """Test listing reviews."""
    # Create multiple reviews
    for i in range(3):
        review = Review(
            task_type=f"test_{i}",
            proposed_action=f"Test action {i}",
            urgency=UrgencyLevel.MEDIUM.value,
            status=ReviewStatus.PENDING.value,
        )
        await review_repo.create(review)
    
    reviews = await review_repo.list()
    assert len(reviews) >= 3


@pytest.mark.asyncio
async def test_review_repository_list_by_status(review_repo: ReviewRepository):
    """Test listing reviews by status."""
    # Create reviews with different statuses
    for status in [ReviewStatus.PENDING, ReviewStatus.APPROVED]:
        review = Review(
            task_type="test",
            proposed_action="Test action",
            urgency=UrgencyLevel.MEDIUM.value,
            status=status.value,
        )
        await review_repo.create(review)
    
    pending = await review_repo.list_by_status(ReviewStatus.PENDING)
    assert len(pending) >= 1
    assert all(r.status == ReviewStatus.PENDING.value for r in pending)


@pytest.mark.asyncio
async def test_review_repository_get_with_relationships(review_repo: ReviewRepository, decision_repo: DecisionRepository):
    """Test getting review with relationships."""
    review = Review(
        task_type="test",
        proposed_action="Test action",
        urgency=UrgencyLevel.MEDIUM.value,
        status=ReviewStatus.PENDING.value,
    )
    created_review = await review_repo.create(review)
    
    decision = Decision(
        review_id=created_review.id,
        decision_type=DecisionType.APPROVE.value,
    )
    await decision_repo.create(decision)
    
    review_with_decision = await review_repo.get_with_relationships(created_review.id)
    assert review_with_decision is not None
    assert review_with_decision.decision is not None
    assert review_with_decision.decision.decision_type == DecisionType.APPROVE.value


@pytest.mark.asyncio
async def test_review_repository_delete(review_repo: ReviewRepository):
    """Test deleting a review."""
    review = Review(
        task_type="test",
        proposed_action="Test action",
        urgency=UrgencyLevel.MEDIUM.value,
        status=ReviewStatus.PENDING.value,
    )
    created = await review_repo.create(review)
    
    deleted = await review_repo.delete(created.id)
    assert deleted is True
    
    retrieved = await review_repo.get(created.id)
    assert retrieved is None


@pytest.mark.asyncio
async def test_decision_repository_create(decision_repo: DecisionRepository, review_repo: ReviewRepository):
    """Test creating a decision."""
    review = Review(
        task_type="test",
        proposed_action="Test action",
        urgency=UrgencyLevel.MEDIUM.value,
        status=ReviewStatus.PENDING.value,
    )
    created_review = await review_repo.create(review)
    
    decision = Decision(
        review_id=created_review.id,
        decision_type=DecisionType.APPROVE.value,
        notes="Test notes",
    )
    
    created = await decision_repo.create(decision)
    assert created.id is not None
    assert created.decision_type == DecisionType.APPROVE.value


@pytest.mark.asyncio
async def test_decision_repository_get_by_review_id(decision_repo: DecisionRepository, review_repo: ReviewRepository):
    """Test getting decision by review ID."""
    review = Review(
        task_type="test",
        proposed_action="Test action",
        urgency=UrgencyLevel.MEDIUM.value,
        status=ReviewStatus.PENDING.value,
    )
    created_review = await review_repo.create(review)
    
    decision = Decision(
        review_id=created_review.id,
        decision_type=DecisionType.APPROVE.value,
    )
    await decision_repo.create(decision)
    
    retrieved = await decision_repo.get_by_review_id(created_review.id)
    assert retrieved is not None
    assert retrieved.review_id == created_review.id


@pytest.mark.asyncio
async def test_feedback_repository_create(feedback_repo: FeedbackRepository, review_repo: ReviewRepository):
    """Test creating feedback."""
    review = Review(
        task_type="test",
        proposed_action="Test action",
        urgency=UrgencyLevel.MEDIUM.value,
        status=ReviewStatus.PENDING.value,
    )
    created_review = await review_repo.create(review)
    
    feedback = Feedback(
        review_id=created_review.id,
        rating=5,
        comment="Great!",
    )
    
    created = await feedback_repo.create(feedback)
    assert created.id is not None
    assert created.rating == 5


@pytest.mark.asyncio
async def test_feedback_repository_get_by_review_id(feedback_repo: FeedbackRepository, review_repo: ReviewRepository):
    """Test getting feedback by review ID."""
    review = Review(
        task_type="test",
        proposed_action="Test action",
        urgency=UrgencyLevel.MEDIUM.value,
        status=ReviewStatus.PENDING.value,
    )
    created_review = await review_repo.create(review)
    
    feedback = Feedback(
        review_id=created_review.id,
        rating=5,
    )
    await feedback_repo.create(feedback)
    
    feedbacks = await feedback_repo.get_by_review_id(created_review.id)
    assert len(feedbacks) >= 1
    assert feedbacks[0].rating == 5


@pytest.mark.asyncio
async def test_assignment_repository_create(assignment_repo: AssignmentRepository, review_repo: ReviewRepository):
    """Test creating an assignment."""
    review = Review(
        task_type="test",
        proposed_action="Test action",
        urgency=UrgencyLevel.MEDIUM.value,
        status=ReviewStatus.PENDING.value,
    )
    created_review = await review_repo.create(review)
    
    assignment = ReviewAssignment(
        review_id=created_review.id,
        reviewer_identifier="test@example.com",
    )
    
    created = await assignment_repo.create(assignment)
    assert created.id is not None
    assert created.reviewer_identifier == "test@example.com"


@pytest.mark.asyncio
async def test_attachment_repository_create(attachment_repo: AttachmentRepository, review_repo: ReviewRepository):
    """Test creating an attachment."""
    review = Review(
        task_type="test",
        proposed_action="Test action",
        urgency=UrgencyLevel.MEDIUM.value,
        status=ReviewStatus.PENDING.value,
    )
    created_review = await review_repo.create(review)
    
    attachment = Attachment(
        review_id=created_review.id,
        file_name="test.txt",
        content_type="text/plain",
        content_category=ContentCategory.TEXT.value,
        file_size=100,
        storage_key="test/key",
        storage_provider="local",
    )
    
    created = await attachment_repo.create(attachment)
    assert created.id is not None
    assert created.file_name == "test.txt"


@pytest.mark.asyncio
async def test_attachment_repository_get_by_storage_key(attachment_repo: AttachmentRepository, review_repo: ReviewRepository):
    """Test getting attachment by storage key."""
    review = Review(
        task_type="test",
        proposed_action="Test action",
        urgency=UrgencyLevel.MEDIUM.value,
        status=ReviewStatus.PENDING.value,
    )
    created_review = await review_repo.create(review)
    
    attachment = Attachment(
        review_id=created_review.id,
        file_name="test.txt",
        content_type="text/plain",
        content_category=ContentCategory.TEXT.value,
        file_size=100,
        storage_key="unique/key",
        storage_provider="local",
    )
    await attachment_repo.create(attachment)
    
    retrieved = await attachment_repo.get_by_storage_key("unique/key")
    assert retrieved is not None
    assert retrieved.storage_key == "unique/key"

