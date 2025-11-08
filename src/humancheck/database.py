"""Database connection and session management."""
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from sqlalchemy import create_engine
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker


class Base(DeclarativeBase):
    """Base class for all database models."""
    pass


class Database:
    """Database connection manager."""

    def __init__(self, url: str, echo: bool = False):
        """Initialize database connection.

        Args:
            url: Database URL (e.g., 'sqlite:///humancheck.db' or 'postgresql+asyncpg://...')
            echo: Whether to log SQL statements
        """
        self.url = url
        self.echo = echo

        # Determine if we're using async or sync based on URL
        self.is_async = "+asyncpg" in url or "+aiosqlite" in url

        if self.is_async:
            self.engine = create_async_engine(url, echo=echo)
            self.session_factory = async_sessionmaker(
                self.engine, class_=AsyncSession, expire_on_commit=False
            )
        else:
            self.engine = create_engine(url, echo=echo)
            self.session_factory = sessionmaker(self.engine, expire_on_commit=False)

    async def create_tables(self):
        """Create all tables in the database."""
        if self.is_async:
            async with self.engine.begin() as conn:
                await conn.run_sync(Base.metadata.create_all)
        else:
            Base.metadata.create_all(self.engine)

    async def drop_tables(self):
        """Drop all tables in the database."""
        if self.is_async:
            async with self.engine.begin() as conn:
                await conn.run_sync(Base.metadata.drop_all)
        else:
            Base.metadata.drop_all(self.engine)

    @asynccontextmanager
    async def session(self) -> AsyncGenerator[Session | AsyncSession, None]:
        """Get a database session.

        Yields:
            Database session (async or sync depending on engine type)
        """
        session = self.session_factory()
        try:
            yield session
            if self.is_async:
                await session.commit()
            else:
                session.commit()
        except Exception:
            if self.is_async:
                await session.rollback()
            else:
                session.rollback()
            raise
        finally:
            if self.is_async:
                await session.close()
            else:
                session.close()

    async def close(self):
        """Close database connection."""
        if self.is_async:
            await self.engine.dispose()
        else:
            self.engine.dispose()


# Global database instance
_db: Database | None = None


def init_db(url: str, echo: bool = False) -> Database:
    """Initialize the global database instance.

    Args:
        url: Database URL
        echo: Whether to log SQL statements

    Returns:
        Database instance
    """
    global _db
    _db = Database(url, echo)
    return _db


def get_db() -> Database:
    """Get the global database instance.

    Returns:
        Database instance

    Raises:
        RuntimeError: If database has not been initialized
    """
    if _db is None:
        raise RuntimeError("Database not initialized. Call init_db() first.")
    return _db
