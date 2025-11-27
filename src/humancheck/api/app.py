"""FastAPI app factory"""
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from ..core.config.settings import get_config
from ..core.storage.database import init_db
from ..core.adapters import RestAdapter, register_adapter
from ..core.file_storage import get_storage_manager

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan context manager.
    
    Handles startup and shutdown events for the FastAPI application.
    """
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

    # Store in app state for access in routes
    app.state.db = db
    app.state.config = config

    logger.info("Humancheck API started")

    yield

    # Shutdown
    await db.close()
    logger.info("Humancheck API stopped")


def create_app() -> FastAPI:
    """Create FastAPI application.
    
    Returns:
        Configured FastAPI application instance
    """
    app = FastAPI(
        title="Humancheck API",
        description="Human-in-the-loop operations platform for AI agents",
        version="0.1.1",
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

    # Register routes
    from .routes import reviews, decisions, feedback, attachments, stats

    app.include_router(reviews.router, tags=["reviews"])
    app.include_router(decisions.router, tags=["decisions"])
    app.include_router(feedback.router, tags=["feedback"])
    app.include_router(attachments.router, tags=["attachments"])
    app.include_router(stats.router, tags=["stats"])

    @app.get("/health")
    async def health():
        """Health check endpoint."""
        return {"status": "healthy", "service": "humancheck"}

    return app


# For backward compatibility - create app instance
app = create_app()

