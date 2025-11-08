"""Test database connection."""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "src"))

from humancheck.config import init_config
from humancheck.database import init_db
from humancheck.models import Review
from sqlalchemy import select


async def main():
    """Test database connection and query."""
    print("Initializing config...")
    config = init_config()

    print(f"Database URL: {config.get_database_url()}")

    print("Initializing database...")
    db = init_db(config.get_database_url())

    print("Creating tables...")
    await db.create_tables()

    print("Testing query...")
    async with db.session() as session:
        query = select(Review).order_by(Review.created_at.desc())
        result = await session.execute(query)
        reviews = list(result.scalars().all())
        print(f"Found {len(reviews)} reviews")

    print("✅ Database connection test successful!")

    await db.close()


if __name__ == "__main__":
    asyncio.run(main())
