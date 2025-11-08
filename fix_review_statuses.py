"""Fix review statuses to match their decisions."""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "src"))

from humancheck.config import init_config
from humancheck.database import init_db
from humancheck.models import Decision, DecisionType, Review, ReviewStatus


async def main():
    config = init_config()
    db = init_db(config.get_database_url())

    async with db.session() as session:
        from sqlalchemy import select

        # Get all reviews with decisions
        reviews = await session.execute(
            select(Review).join(Decision, Review.id == Decision.review_id)
        )
        reviews = reviews.scalars().all()

        print(f"Found {len(reviews)} reviews with decisions")

        for review in reviews:
            # Get the decision
            decision_query = await session.execute(
                select(Decision).where(Decision.review_id == review.id)
            )
            decision = decision_query.scalar_one_or_none()

            if decision:
                # Determine what the status should be
                expected_status = None
                if decision.decision_type == DecisionType.APPROVE.value:
                    expected_status = ReviewStatus.APPROVED.value
                elif decision.decision_type == DecisionType.REJECT.value:
                    expected_status = ReviewStatus.REJECTED.value
                elif decision.decision_type == DecisionType.MODIFY.value:
                    expected_status = ReviewStatus.MODIFIED.value

                if expected_status and review.status != expected_status:
                    print(f"Fixing Review {review.id}: {review.status} -> {expected_status}")
                    review.status = expected_status
                else:
                    print(f"Review {review.id}: Status is correct ({review.status})")

        await session.commit()
        print("\n✅ Database fixed!")


if __name__ == "__main__":
    asyncio.run(main())
