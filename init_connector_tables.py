"""Initialize database tables for connectors."""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "src"))

from humancheck.config import init_config
from humancheck.database import init_db


async def main():
    """Initialize connector tables."""
    print("Initializing connector tables...")

    config = init_config()
    db = init_db(config.get_database_url())

    # Import all models to ensure they're registered
    from humancheck import connector_models  # noqa
    from humancheck import models  # noqa
    from humancheck import platform_models  # noqa

    # Create all tables
    await db.create_tables()

    print("✅ Connector tables created successfully!")


if __name__ == "__main__":
    asyncio.run(main())
