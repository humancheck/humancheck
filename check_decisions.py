"""Check decisions in database."""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "src"))

from humancheck.config import init_config
from humancheck.database import init_db
from humancheck.models import Decision, Review


async def main():
    config = init_config()
    db = init_db(config.get_database_url())

    async with db.session() as session:
        from sqlalchemy import select

        # Get all reviews
        reviews = await session.execute(select(Review))
        reviews = reviews.scalars().all()

        print(f"Found {len(reviews)} reviews")
        for review in reviews:
            print(f"\nReview {review.id}: {review.task_type} - Status: {review.status}")

            # Check for decision
            decision_query = await session.execute(
                select(Decision).where(Decision.review_id == review.id)
            )
            decision = decision_query.scalar_one_or_none()
            if decision:
                print(f"  Decision: {decision.decision_type} (ID: {decision.id})")
            else:
                print(f"  No decision")


if __name__ == "__main__":
    asyncio.run(main())
