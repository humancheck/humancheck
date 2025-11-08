"""FastAPI REST API for Humancheck platform."""
import hashlib
import io
import logging
from contextlib import asynccontextmanager
from typing import List, Optional
from uuid import uuid4

from fastapi import Depends, FastAPI, File, HTTPException, Query, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from .adapters import RestAdapter, get_adapter, register_adapter
from .config import get_config
from .database import get_db, init_db
from .models import Attachment, ContentCategory, Decision, DecisionType, Feedback, Review, ReviewStatus
from .platform_models import Agent, Organization, RoutingRule, Team, User
from .routing import RoutingEngine
from .security import validate_file
from .security.content_validator import sanitize_filename
from .storage import get_storage_manager
from .schemas import (
    AgentCreate,
    AgentResponse,
    DecisionCreate,
    DecisionResponse,
    FeedbackCreate,
    FeedbackResponse,
    OrganizationCreate,
    OrganizationResponse,
    ReviewCreate,
    ReviewList,
    ReviewResponse,
    ReviewStats,
    RoutingRuleCreate,
    RoutingRuleResponse,
    TeamCreate,
    TeamResponse,
    UserCreate,
    UserResponse,
)

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan context manager for startup and shutdown events."""
    # Startup
    config = get_config()
    db = init_db(config.get_database_url())
    await db.create_tables()

    # Register adapters
    rest_adapter = RestAdapter(db.session)
    register_adapter(rest_adapter)

    # Initialize storage
    storage_manager = get_storage_manager()
    storage_manager.initialize(provider_type="local", base_path="./storage")

    logger.info("Humancheck API started")

    yield

    # Shutdown
    await db.close()
    logger.info("Humancheck API stopped")


# Create FastAPI app
app = FastAPI(
    title="Humancheck API",
    description="Human-in-the-loop operations platform for AI agents",
    version="0.1.0",
    lifespan=lifespan,
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Dependency to get database session
async def get_session() -> AsyncSession:
    """Get database session dependency."""
    db = get_db()
    async with db.session() as session:
        yield session


# ========== Review Endpoints ==========

@app.post("/reviews", response_model=ReviewResponse, status_code=201)
async def create_review(
    review_data: ReviewCreate,
    session: AsyncSession = Depends(get_session),
):
    """Create a new review request.

    This endpoint accepts review requests from any framework and creates
    a review entry in the database. The review is then routed to appropriate
    reviewers based on routing rules.
    """
    try:
        # Create review
        review = Review(
            task_type=review_data.task_type,
            proposed_action=review_data.proposed_action,
            agent_reasoning=review_data.agent_reasoning,
            confidence_score=review_data.confidence_score,
            urgency=review_data.urgency.value,
            framework=review_data.framework,
            meta_data=review_data.metadata,
            organization_id=review_data.organization_id,
            agent_id=review_data.agent_id,
            status=ReviewStatus.PENDING.value,
        )

        session.add(review)
        await session.flush()

        # Route the review
        routing_engine = RoutingEngine()
        await routing_engine.route_review(review, session)

        await session.commit()
        await session.refresh(review)

        # If blocking, wait for decision
        if review_data.blocking:
            adapter = get_adapter("rest")
            if adapter:
                try:
                    result = await adapter.handle_blocking(review.id, timeout=300.0)
                    return result
                except TimeoutError:
                    raise HTTPException(
                        status_code=408,
                        detail="Review request timed out waiting for decision"
                    )

        return review

    except Exception as e:
        await session.rollback()
        logger.error(f"Error creating review: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/reviews", response_model=ReviewList)
async def list_reviews(
    status: Optional[str] = Query(None, description="Filter by status"),
    framework: Optional[str] = Query(None, description="Filter by framework"),
    task_type: Optional[str] = Query(None, description="Filter by task type"),
    organization_id: Optional[int] = Query(None, description="Filter by organization"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    session: AsyncSession = Depends(get_session),
):
    """List reviews with optional filtering and pagination."""
    try:
        # Build query
        query = select(Review)

        if status:
            query = query.where(Review.status == status)
        if framework:
            query = query.where(Review.framework == framework)
        if task_type:
            query = query.where(Review.task_type == task_type)
        if organization_id:
            query = query.where(Review.organization_id == organization_id)

        # Get total count
        count_query = select(func.count()).select_from(query.subquery())
        total_result = await session.execute(count_query)
        total = total_result.scalar_one()

        # Apply pagination
        offset = (page - 1) * page_size
        query = query.offset(offset).limit(page_size).order_by(Review.created_at.desc())

        result = await session.execute(query)
        reviews = list(result.scalars().all())

        return ReviewList(
            reviews=reviews,
            total=total,
            page=page,
            page_size=page_size,
        )

    except Exception as e:
        logger.error(f"Error listing reviews: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/reviews/{review_id}", response_model=ReviewResponse)
async def get_review(
    review_id: int,
    session: AsyncSession = Depends(get_session),
):
    """Get a specific review by ID."""
    review = await session.get(Review, review_id)
    if not review:
        raise HTTPException(status_code=404, detail="Review not found")
    return review


@app.post("/reviews/{review_id}/decide", response_model=DecisionResponse)
async def create_decision(
    review_id: int,
    decision_data: DecisionCreate,
    session: AsyncSession = Depends(get_session),
):
    """Make a decision on a review request.

    This endpoint allows reviewers to approve, reject, or modify a review request.
    """
    try:
        # Get the review
        review = await session.get(Review, review_id)
        if not review:
            raise HTTPException(status_code=404, detail="Review not found")

        # Check if decision already exists
        existing_decision = await session.get(Decision, review_id)
        if existing_decision:
            raise HTTPException(
                status_code=409,
                detail="Decision already exists for this review"
            )

        # Create decision
        decision = Decision(
            review_id=review_id,
            reviewer_id=decision_data.reviewer_id,
            decision_type=decision_data.decision_type.value,
            modified_action=decision_data.modified_action,
            notes=decision_data.notes,
        )

        session.add(decision)

        # Update review status
        if decision_data.decision_type == DecisionType.APPROVE:
            review.status = ReviewStatus.APPROVED.value
        elif decision_data.decision_type == DecisionType.REJECT:
            review.status = ReviewStatus.REJECTED.value
        elif decision_data.decision_type == DecisionType.MODIFY:
            review.status = ReviewStatus.MODIFIED.value

        await session.commit()
        await session.refresh(decision)

        return decision

    except HTTPException:
        raise
    except Exception as e:
        await session.rollback()
        logger.error(f"Error creating decision: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/reviews/{review_id}/decision", response_model=Optional[DecisionResponse])
async def get_decision(
    review_id: int,
    session: AsyncSession = Depends(get_session),
):
    """Get the decision for a review request."""
    decision = await session.get(Decision, review_id)
    return decision


@app.post("/reviews/{review_id}/feedback", response_model=FeedbackResponse, status_code=201)
async def submit_feedback(
    review_id: int,
    feedback_data: FeedbackCreate,
    session: AsyncSession = Depends(get_session),
):
    """Submit feedback on a review/decision."""
    try:
        # Verify review exists
        review = await session.get(Review, review_id)
        if not review:
            raise HTTPException(status_code=404, detail="Review not found")

        # Create feedback
        feedback = Feedback(
            review_id=review_id,
            rating=feedback_data.rating,
            comment=feedback_data.comment,
        )

        session.add(feedback)
        await session.commit()
        await session.refresh(feedback)

        return feedback

    except HTTPException:
        raise
    except Exception as e:
        await session.rollback()
        logger.error(f"Error submitting feedback: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ========== Statistics Endpoint ==========

@app.get("/stats", response_model=ReviewStats)
async def get_statistics(
    organization_id: Optional[int] = Query(None, description="Filter by organization"),
    session: AsyncSession = Depends(get_session),
):
    """Get review statistics and analytics."""
    try:
        # Build base query
        query = select(Review)
        if organization_id:
            query = query.where(Review.organization_id == organization_id)

        result = await session.execute(query)
        reviews = list(result.scalars().all())

        # Calculate statistics
        total_reviews = len(reviews)
        pending_reviews = sum(1 for r in reviews if r.status == ReviewStatus.PENDING.value)
        approved_reviews = sum(1 for r in reviews if r.status == ReviewStatus.APPROVED.value)
        rejected_reviews = sum(1 for r in reviews if r.status == ReviewStatus.REJECTED.value)
        modified_reviews = sum(1 for r in reviews if r.status == ReviewStatus.MODIFIED.value)

        # Average confidence score
        confidence_scores = [r.confidence_score for r in reviews if r.confidence_score is not None]
        avg_confidence = sum(confidence_scores) / len(confidence_scores) if confidence_scores else None

        # Task type breakdown
        task_type_breakdown = {}
        for review in reviews:
            task_type_breakdown[review.task_type] = task_type_breakdown.get(review.task_type, 0) + 1

        # Framework breakdown
        framework_breakdown = {}
        for review in reviews:
            if review.framework:
                framework_breakdown[review.framework] = framework_breakdown.get(review.framework, 0) + 1

        # Urgency breakdown
        urgency_breakdown = {}
        for review in reviews:
            urgency_breakdown[review.urgency] = urgency_breakdown.get(review.urgency, 0) + 1

        return ReviewStats(
            total_reviews=total_reviews,
            pending_reviews=pending_reviews,
            approved_reviews=approved_reviews,
            rejected_reviews=rejected_reviews,
            modified_reviews=modified_reviews,
            avg_confidence_score=avg_confidence,
            task_type_breakdown=task_type_breakdown,
            framework_breakdown=framework_breakdown,
            urgency_breakdown=urgency_breakdown,
        )

    except Exception as e:
        logger.error(f"Error getting statistics: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ========== Organization Endpoints ==========

@app.post("/organizations", response_model=OrganizationResponse, status_code=201)
async def create_organization(
    org_data: OrganizationCreate,
    session: AsyncSession = Depends(get_session),
):
    """Create a new organization."""
    try:
        org = Organization(name=org_data.name, settings=org_data.settings)
        session.add(org)
        await session.commit()
        await session.refresh(org)
        return org
    except Exception as e:
        await session.rollback()
        logger.error(f"Error creating organization: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/organizations/{org_id}", response_model=OrganizationResponse)
async def get_organization(org_id: int, session: AsyncSession = Depends(get_session)):
    """Get an organization by ID."""
    org = await session.get(Organization, org_id)
    if not org:
        raise HTTPException(status_code=404, detail="Organization not found")
    return org


# ========== User Endpoints ==========

@app.post("/users", response_model=UserResponse, status_code=201)
async def create_user(
    user_data: UserCreate,
    session: AsyncSession = Depends(get_session),
):
    """Create a new user."""
    try:
        user = User(
            email=user_data.email,
            name=user_data.name,
            role=user_data.role,
            organization_id=user_data.organization_id,
        )
        session.add(user)
        await session.commit()
        await session.refresh(user)
        return user
    except Exception as e:
        await session.rollback()
        logger.error(f"Error creating user: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ========== Team Endpoints ==========

@app.post("/teams", response_model=TeamResponse, status_code=201)
async def create_team(
    team_data: TeamCreate,
    session: AsyncSession = Depends(get_session),
):
    """Create a new team."""
    try:
        team = Team(
            name=team_data.name,
            organization_id=team_data.organization_id,
            settings=team_data.settings,
        )
        session.add(team)
        await session.commit()
        await session.refresh(team)
        return team
    except Exception as e:
        await session.rollback()
        logger.error(f"Error creating team: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ========== Agent Endpoints ==========

@app.post("/agents", response_model=AgentResponse, status_code=201)
async def create_agent(
    agent_data: AgentCreate,
    session: AsyncSession = Depends(get_session),
):
    """Register a new AI agent."""
    try:
        agent = Agent(
            name=agent_data.name,
            framework=agent_data.framework,
            organization_id=agent_data.organization_id,
            description=agent_data.description,
            meta_data=agent_data.metadata,
        )
        session.add(agent)
        await session.commit()
        await session.refresh(agent)
        return agent
    except Exception as e:
        await session.rollback()
        logger.error(f"Error creating agent: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ========== Routing Rule Endpoints ==========

@app.post("/routing-rules", response_model=RoutingRuleResponse, status_code=201)
async def create_routing_rule(
    rule_data: RoutingRuleCreate,
    session: AsyncSession = Depends(get_session),
):
    """Create a new routing rule."""
    try:
        rule = RoutingRule(
            name=rule_data.name,
            organization_id=rule_data.organization_id,
            priority=rule_data.priority,
            conditions=rule_data.conditions,
            assign_to_user_id=rule_data.assign_to_user_id,
            assign_to_team_id=rule_data.assign_to_team_id,
            is_active=rule_data.is_active,
        )
        session.add(rule)
        await session.commit()
        await session.refresh(rule)
        return rule
    except Exception as e:
        await session.rollback()
        logger.error(f"Error creating routing rule: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ========== Attachment Endpoints ==========

def _detect_content_category(content_type: str) -> str:
    """Detect content category from MIME type."""
    if content_type.startswith("text/"):
        return ContentCategory.TEXT.value
    elif content_type.startswith("image/"):
        return ContentCategory.IMAGE.value
    elif content_type.startswith("audio/"):
        return ContentCategory.AUDIO.value
    elif content_type.startswith("video/"):
        return ContentCategory.VIDEO.value
    elif content_type == "application/pdf":
        return ContentCategory.DOCUMENT.value
    else:
        return ContentCategory.OTHER.value


@app.post("/reviews/{review_id}/attachments", status_code=201)
async def upload_attachment(
    review_id: int,
    file: UploadFile = File(...),
    description: Optional[str] = Query(None, description="Optional description"),
    session: AsyncSession = Depends(get_session),
):
    """Upload an attachment to a review."""
    try:
        # Check if review exists
        result = await session.execute(select(Review).where(Review.id == review_id))
        review = result.scalar_one_or_none()

        if not review:
            raise HTTPException(status_code=404, detail=f"Review {review_id} not found")

        # Read file content
        content = await file.read()
        file_size = len(content)

        # Detect content category
        content_category = _detect_content_category(file.content_type or "application/octet-stream")

        # Validate file
        is_valid, error, validation_metadata = validate_file(
            content,
            file.content_type or "application/octet-stream",
            content_category
        )

        if not is_valid:
            raise HTTPException(status_code=400, detail=f"File validation failed: {error}")

        # Get checksum from validation metadata
        checksum = validation_metadata.get("checksum")

        # Sanitize filename
        safe_filename = sanitize_filename(file.filename or "unnamed")

        # Generate storage key
        storage_key = f"reviews/{review_id}/attachments/{uuid4()}/{safe_filename}"

        # Upload to storage
        storage = get_storage_manager().get()
        await storage.upload(
            file=io.BytesIO(content),
            key=storage_key,
            content_type=file.content_type or "application/octet-stream",
            metadata={"review_id": review_id, "file_name": safe_filename},
        )

        # Get URLs
        preview_url = await storage.get_url(storage_key, expires_in=3600, download=False)
        download_url = await storage.get_url(storage_key, expires_in=3600, download=True)

        # For text files, store inline content
        inline_content = None
        if content_category == ContentCategory.TEXT.value and file_size < 1024 * 1024:  # < 1MB
            inline_content = content.decode("utf-8", errors="replace")

        # Create attachment record
        attachment = Attachment(
            review_id=review_id,
            file_name=safe_filename,
            content_type=file.content_type or "application/octet-stream",
            content_category=content_category,
            file_size=file_size,
            storage_key=storage_key,
            storage_provider="local",
            inline_content=inline_content,
            preview_url=preview_url,
            download_url=download_url,
            description=description,
            checksum=checksum,
            file_metadata={
                "original_filename": file.filename,
                "sanitized_filename": safe_filename,
                "upload_method": "api",
                "validation": validation_metadata,
            },
        )

        session.add(attachment)
        await session.commit()
        await session.refresh(attachment)

        return attachment

    except HTTPException:
        raise
    except Exception as e:
        await session.rollback()
        logger.error(f"Error uploading attachment: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/reviews/{review_id}/attachments")
async def list_attachments(
    review_id: int,
    session: AsyncSession = Depends(get_session),
):
    """List all attachments for a review."""
    try:
        # Check if review exists
        result = await session.execute(select(Review).where(Review.id == review_id))
        review = result.scalar_one_or_none()

        if not review:
            raise HTTPException(status_code=404, detail=f"Review {review_id} not found")

        # Get attachments
        result = await session.execute(
            select(Attachment)
            .where(Attachment.review_id == review_id)
            .order_by(Attachment.uploaded_at.desc())
        )
        attachments = list(result.scalars().all())

        return {"review_id": review_id, "attachments": attachments, "count": len(attachments)}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error listing attachments: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/attachments/{attachment_id}")
async def get_attachment(
    attachment_id: int,
    session: AsyncSession = Depends(get_session),
):
    """Get attachment metadata."""
    try:
        result = await session.execute(select(Attachment).where(Attachment.id == attachment_id))
        attachment = result.scalar_one_or_none()

        if not attachment:
            raise HTTPException(status_code=404, detail=f"Attachment {attachment_id} not found")

        return attachment

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting attachment: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/attachments/{attachment_id}/download")
async def download_attachment(
    attachment_id: int,
    disposition: str = Query("inline", description="Content disposition: inline or attachment"),
    session: AsyncSession = Depends(get_session),
):
    """Download attachment file."""
    try:
        result = await session.execute(select(Attachment).where(Attachment.id == attachment_id))
        attachment = result.scalar_one_or_none()

        if not attachment:
            raise HTTPException(status_code=404, detail=f"Attachment {attachment_id} not found")

        # Download from storage
        storage = get_storage_manager().get()
        content = await storage.download(attachment.storage_key)

        # Return as streaming response
        return StreamingResponse(
            io.BytesIO(content),
            media_type=attachment.content_type,
            headers={
                "Content-Disposition": f'{disposition}; filename="{attachment.file_name}"',
                "Content-Length": str(len(content)),
            },
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error downloading attachment: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/attachments/{attachment_id}", status_code=204)
async def delete_attachment(
    attachment_id: int,
    session: AsyncSession = Depends(get_session),
):
    """Delete an attachment."""
    try:
        result = await session.execute(select(Attachment).where(Attachment.id == attachment_id))
        attachment = result.scalar_one_or_none()

        if not attachment:
            raise HTTPException(status_code=404, detail=f"Attachment {attachment_id} not found")

        # Delete from storage
        storage = get_storage_manager().get()
        await storage.delete(attachment.storage_key)

        # Delete from database
        await session.delete(attachment)
        await session.commit()

        return None

    except HTTPException:
        raise
    except Exception as e:
        await session.rollback()
        logger.error(f"Error deleting attachment: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ========== Health Check ==========

@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "service": "humancheck"}
