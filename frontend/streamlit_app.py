"""Streamlit dashboard for Humancheck review queue.

This provides a real-time interface for human reviewers to view pending
reviews, make decisions, and track statistics.
"""
import asyncio
import json
import os
import sys
from datetime import datetime
from pathlib import Path

import streamlit as st

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from humancheck.config import get_config, init_config
from humancheck.database import init_db
from humancheck.models import Attachment, Decision, DecisionType, Review, ReviewStatus
from humancheck.platform_models import User
from humancheck.dashboard.preview import render_preview_panel


# Page configuration
st.set_page_config(
    page_title="Humancheck Dashboard",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded",
)


# Initialize database
@st.cache_resource
def initialize():
    """Initialize configuration and database."""
    config = init_config()
    db = init_db(config.get_database_url())

    # Create tables synchronously for Streamlit
    import asyncio
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

    loop.run_until_complete(db.create_tables())
    return config, db


config, db = initialize()


def run_async(coro):
    """Run async function in Streamlit."""
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

    return loop.run_until_complete(coro)


async def get_reviews(status_filter=None, task_type_filter=None):
    """Get reviews from database."""
    async with db.session() as session:
        from sqlalchemy import select

        query = select(Review).order_by(Review.created_at.desc())

        if status_filter and status_filter != "All":
            query = query.where(Review.status == status_filter.lower())

        if task_type_filter and task_type_filter != "All":
            query = query.where(Review.task_type == task_type_filter)

        result = await session.execute(query)
        reviews = list(result.scalars().all())

        # Detach from session to avoid lazy loading issues
        for review in reviews:
            session.expunge(review)

        return reviews


async def get_review_with_decision(review_id):
    """Get review with its decision."""
    async with db.session() as session:
        from sqlalchemy.orm import selectinload
        from sqlalchemy import select

        # Eagerly load the decision relationship
        query = select(Review).where(Review.id == review_id).options(selectinload(Review.decision))
        result = await session.execute(query)
        review = result.scalar_one_or_none()

        if review:
            # Access decision before expunging to ensure it's loaded
            decision = review.decision
            session.expunge(review)
            # Only expunge decision if it's actually in the session
            if decision and decision in session:
                session.expunge(decision)
        return review


async def get_attachments(review_id):
    """Get attachments for a review."""
    async with db.session() as session:
        from sqlalchemy import select

        query = select(Attachment).where(Attachment.review_id == review_id).order_by(Attachment.uploaded_at.desc())
        result = await session.execute(query)
        attachments = list(result.scalars().all())

        # Detach from session
        for attachment in attachments:
            session.expunge(attachment)

        return attachments


async def create_decision(review_id, decision_type, modified_action=None, notes=None, reviewer_id=None):
    """Create a decision for a review.

    Returns:
        True: Success
        "decision_exists": Decision already exists
        "review_not_found": Review not found
        False: Other error
    """
    from sqlalchemy import select

    try:
        async with db.session() as session:
            review = await session.get(Review, review_id)
            if not review:
                return "review_not_found"

            # Check if decision already exists for this review
            stmt = select(Decision).where(Decision.review_id == review_id)
            result = await session.execute(stmt)
            existing_decision = result.scalar_one_or_none()
            if existing_decision:
                return "decision_exists"

            decision = Decision(
                review_id=review_id,
                reviewer_id=reviewer_id,
                decision_type=decision_type,
                modified_action=modified_action,
                notes=notes,
            )

            session.add(decision)

            # Update review status
            if decision_type == DecisionType.APPROVE.value:
                review.status = ReviewStatus.APPROVED.value
            elif decision_type == DecisionType.REJECT.value:
                review.status = ReviewStatus.REJECTED.value
            elif decision_type == DecisionType.MODIFY.value:
                review.status = ReviewStatus.MODIFIED.value

            await session.commit()
            return True
    except Exception as e:
        import sys
        import traceback
        print(f"Error creating decision: {type(e).__name__}: {e}", file=sys.stderr, flush=True)
        traceback.print_exc()
        return False


async def get_statistics():
    """Get dashboard statistics."""
    async with db.session() as session:
        from sqlalchemy import func, select

        # Count reviews by status
        result = await session.execute(select(func.count(Review.id)))
        total = result.scalar_one()

        result = await session.execute(
            select(func.count(Review.id)).where(Review.status == ReviewStatus.PENDING.value)
        )
        pending = result.scalar_one()

        result = await session.execute(
            select(func.count(Review.id)).where(Review.status == ReviewStatus.APPROVED.value)
        )
        approved = result.scalar_one()

        result = await session.execute(
            select(func.count(Review.id)).where(Review.status == ReviewStatus.REJECTED.value)
        )
        rejected = result.scalar_one()

        result = await session.execute(
            select(func.count(Review.id)).where(Review.status == ReviewStatus.MODIFIED.value)
        )
        modified = result.scalar_one()

        # Average confidence
        result = await session.execute(
            select(func.avg(Review.confidence_score)).where(Review.confidence_score.isnot(None))
        )
        avg_confidence = result.scalar_one()

        return {
            "total": total,
            "pending": pending,
            "approved": approved,
            "rejected": rejected,
            "modified": modified,
            "avg_confidence": avg_confidence or 0,
        }


def extract_tool_info(review):
    """Extract tool call information from review metadata.

    For HITL reviews, this extracts the tool name and arguments
    for better display and editing.

    Returns:
        tuple: (tool_name, tool_args_dict, is_hitl)
    """
    if review.framework == "langchain_hitl" and review.meta_data:
        metadata = review.meta_data
        tool_name = metadata.get("tool_name")
        tool_args = metadata.get("tool_arguments", {})
        return tool_name, tool_args, True
    return None, None, False


# Sidebar
st.sidebar.title("🤖 Humancheck")
st.sidebar.markdown("*Human-in-the-Loop Review Dashboard*")

# Filters
st.sidebar.header("Filters")
status_filter = st.sidebar.selectbox(
    "Status",
    ["All", "Pending", "Approved", "Rejected", "Modified"],
)

# Get unique task types
reviews_for_filter = run_async(get_reviews())
task_types = ["All"] + sorted(list(set(r.task_type for r in reviews_for_filter if r.task_type)))
task_type_filter = st.sidebar.selectbox("Task Type", task_types)

# Auto-refresh
auto_refresh = st.sidebar.checkbox("Auto-refresh (30s)", value=False)
if auto_refresh:
    st.sidebar.info("Dashboard will refresh every 30 seconds")

# Main content
st.title("Review Queue")

# Statistics
stats = run_async(get_statistics())

col1, col2, col3, col4, col5 = st.columns(5)
with col1:
    st.metric("Total Reviews", stats["total"])
with col2:
    st.metric("Pending", stats["pending"], delta=None, delta_color="off")
with col3:
    st.metric("Approved", stats["approved"])
with col4:
    st.metric("Rejected", stats["rejected"])
with col5:
    st.metric("Avg Confidence", f"{stats['avg_confidence']:.2%}" if stats["avg_confidence"] else "N/A")

st.divider()

# Get filtered reviews
reviews = run_async(get_reviews(status_filter, task_type_filter if task_type_filter != "All" else None))

if not reviews:
    st.info("No reviews found matching the filters.")
else:
    st.subheader(f"Reviews ({len(reviews)})")

    # Display reviews
    for review in reviews:
        with st.expander(
            f"[{review.status.upper()}] {review.task_type} - Review #{review.id}",
            expanded=(review.status == ReviewStatus.PENDING.value)
        ):
            # Review details in columns
            col_left, col_right = st.columns([2, 1])

            with col_left:
                st.markdown("**Proposed Action:**")
                st.info(review.proposed_action)

                if review.agent_reasoning:
                    st.markdown("**Agent Reasoning:**")
                    st.write(review.agent_reasoning)

                # Show attachments if any
                attachments = run_async(get_attachments(review.id))
                if attachments:
                    st.divider()
                    st.markdown(f"**Attachments ({len(attachments)}):**")
                    render_preview_panel(attachments)

            with col_right:
                st.markdown("**Details:**")
                st.write(f"**ID:** {review.id}")
                st.write(f"**Task Type:** {review.task_type}")
                st.write(f"**Status:** {review.status}")
                st.write(f"**Urgency:** {review.urgency}")

                if review.confidence_score is not None:
                    st.write(f"**Confidence:** {review.confidence_score:.1%}")

                if review.framework:
                    st.write(f"**Framework:** {review.framework}")

                st.write(f"**Created:** {review.created_at.strftime('%Y-%m-%d %H:%M:%S')}")

            # Decision interface for pending reviews
            if review.status == ReviewStatus.PENDING.value:
                st.divider()
                st.markdown("### Make Decision")

                tab1, tab2, tab3 = st.tabs(["✅ Approve", "❌ Reject", "✏️ Modify"])

                with tab1:
                    notes_approve = st.text_area(
                        "Notes (optional)",
                        key=f"notes_approve_{review.id}",
                        placeholder="Add any notes about this approval..."
                    )

                    # Show LangChain payload preview
                    with st.expander("🔍 View LangChain Resume Payload"):
                        payload = {
                            "decisions": [
                                {
                                    "type": "approve"
                                }
                            ]
                        }
                        st.json(payload)
                        st.code(f"""
# Resume agent with this decision
agent.invoke(
    Command(
        resume={json.dumps(payload, indent=12)}
    ),
    config=config
)""", language="python")

                    if st.button("Approve Action", key=f"approve_{review.id}", type="primary"):
                        result = run_async(
                            create_decision(
                                review.id,
                                DecisionType.APPROVE.value,
                                notes=notes_approve if notes_approve else None
                            )
                        )
                        if result == True:
                            st.success("✅ Review approved!")
                            st.rerun()
                        elif result == "decision_exists":
                            st.warning("⚠️ This review already has a decision. Please refresh the page.")
                        elif result == "review_not_found":
                            st.error("❌ Review not found")
                        else:
                            st.error("❌ Failed to create decision")

                with tab2:
                    notes_reject = st.text_area(
                        "Reason for rejection",
                        key=f"notes_reject_{review.id}",
                        placeholder="Please explain why this action is being rejected..."
                    )

                    # Show LangChain payload preview
                    with st.expander("🔍 View LangChain Resume Payload"):
                        payload = {
                            "decisions": [
                                {
                                    "type": "reject",
                                    "feedback": notes_reject if notes_reject else "Action rejected by human reviewer"
                                }
                            ]
                        }
                        st.json(payload)
                        st.code(f"""
# Resume agent with this decision
agent.invoke(
    Command(
        resume={json.dumps(payload, indent=12)}
    ),
    config=config
)""", language="python")

                    if st.button("Reject Action", key=f"reject_{review.id}", type="secondary"):
                        if not notes_reject:
                            st.warning("Please provide a reason for rejection")
                        else:
                            result = run_async(
                                create_decision(
                                    review.id,
                                    DecisionType.REJECT.value,
                                    notes=notes_reject
                                )
                            )
                            if result == True:
                                st.success("❌ Review rejected")
                                st.rerun()
                            elif result == "decision_exists":
                                st.warning("⚠️ This review already has a decision. Please refresh the page.")
                            elif result == "review_not_found":
                                st.error("❌ Review not found")
                            else:
                                st.error("❌ Failed to create decision")

                with tab3:
                    # Check if this is a HITL tool call for better editing
                    tool_name, tool_args, is_hitl = extract_tool_info(review)

                    if is_hitl and tool_args is not None:
                        st.markdown(f"**Tool:** `{tool_name}`")
                        st.markdown("**Edit Arguments:**")

                        # Allow editing as JSON
                        args_json = json.dumps(tool_args, indent=2)
                        modified_args_text = st.text_area(
                            "Tool Arguments (JSON)",
                            key=f"modified_args_{review.id}",
                            value=args_json,
                            height=200,
                            placeholder='{"arg1": "value1", "arg2": "value2"}'
                        )

                        # Validate JSON
                        try:
                            modified_args = json.loads(modified_args_text)
                            st.success("✅ Valid JSON")
                        except json.JSONDecodeError as e:
                            st.error(f"❌ Invalid JSON: {e}")
                            modified_args = None
                    else:
                        # Regular text editing for non-HITL reviews
                        modified_action = st.text_area(
                            "Modified action",
                            key=f"modified_{review.id}",
                            value=review.proposed_action,
                            placeholder="Enter the modified action..."
                        )

                    notes_modify = st.text_area(
                        "Notes (optional)",
                        key=f"notes_modify_{review.id}",
                        placeholder="Explain the modifications..."
                    )

                    # Show LangChain payload preview
                    with st.expander("🔍 View LangChain Resume Payload"):
                        # Prepare preview payload
                        if is_hitl and tool_args is not None:
                            # For HITL, show the modified args
                            try:
                                preview_modified = json.loads(modified_args_text) if modified_args_text else tool_args
                            except:
                                preview_modified = tool_args
                        else:
                            preview_modified = modified_action if 'modified_action' in locals() else review.proposed_action

                        payload = {
                            "decisions": [
                                {
                                    "type": "modify",
                                    "action": preview_modified,
                                    "feedback": notes_modify if notes_modify else "Action modified by human reviewer"
                                }
                            ]
                        }
                        st.json(payload)
                        st.code(f"""
# Resume agent with this decision
agent.invoke(
    Command(
        resume={json.dumps(payload, indent=12)}
    ),
    config=config
)""", language="python")

                    if st.button("Submit Modified Action", key=f"modify_{review.id}", type="primary"):
                        # Prepare the modified action
                        can_submit = True
                        final_modified_action = None

                        if is_hitl and tool_args is not None:
                            if modified_args is None:
                                st.warning("Please fix the JSON errors before submitting")
                                can_submit = False
                            else:
                                # Store as JSON string for HITL
                                final_modified_action = json.dumps(modified_args)
                        else:
                            if not modified_action:
                                st.warning("Please provide the modified action")
                                can_submit = False
                            else:
                                final_modified_action = modified_action

                        if can_submit:
                            result = run_async(
                                create_decision(
                                    review.id,
                                    DecisionType.MODIFY.value,
                                    modified_action=final_modified_action,
                                    notes=notes_modify if notes_modify else None
                                )
                            )
                            if result == True:
                                st.success("✏️ Action modified and approved")
                                st.rerun()
                            elif result == "decision_exists":
                                st.warning("⚠️ This review already has a decision. Please refresh the page.")
                            elif result == "review_not_found":
                                st.error("❌ Review not found")
                            else:
                                st.error("❌ Failed to create decision")

            # Show decision for completed reviews
            elif review.status != ReviewStatus.PENDING.value:
                review_with_decision = run_async(get_review_with_decision(review.id))
                if review_with_decision and review_with_decision.decision:
                    st.divider()
                    st.markdown("### Decision")

                    decision = review_with_decision.decision

                    if decision.decision_type == DecisionType.APPROVE.value:
                        st.success(f"✅ Approved")
                    elif decision.decision_type == DecisionType.REJECT.value:
                        st.error(f"❌ Rejected")
                    elif decision.decision_type == DecisionType.MODIFY.value:
                        st.warning(f"✏️ Modified")

                    if decision.modified_action:
                        st.markdown("**Modified Action:**")
                        st.info(decision.modified_action)

                    if decision.notes:
                        st.markdown("**Notes:**")
                        st.write(decision.notes)

                    st.caption(f"Decision made at: {decision.timestamp.strftime('%Y-%m-%d %H:%M:%S')}")

# Auto-refresh
if auto_refresh:
    import time
    time.sleep(30)
    st.rerun()
