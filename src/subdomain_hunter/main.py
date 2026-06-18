import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from subdomain_hunter.config import get_settings
from subdomain_hunter.db import init_db
from subdomain_hunter.api import domains, vulnerabilities, scans, export

logger = logging.getLogger(__name__)
settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan context manager for startup and shutdown events."""
    # Startup
    logger.info("Starting up Subdomain Hunter...")
    init_db()
    logger.info("Database initialized")
    
    # Initialize scheduler if needed
    # scheduler.start()
    
    yield
    
    # Shutdown
    logger.info("Shutting down Subdomain Hunter...")
    # scheduler.shutdown()


def create_app() -> FastAPI:
    """Create and configure FastAPI application."""
    app = FastAPI(
        title="Subdomain Hunter",
        description="A comprehensive subdomain security monitoring tool",
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

    # Include routers
    app.include_router(domains.router, prefix="/api/domains", tags=["domains"])
    app.include_router(vulnerabilities.router, prefix="/api/vulnerabilities", tags=["vulnerabilities"])
    app.include_router(scans.router, prefix="/api/scans", tags=["scans"])
    app.include_router(export.router, prefix="/api/export", tags=["export"])

    # Health check endpoint
    @app.get("/health")
    async def health_check():
        return {"status": "healthy"}

    return app


# Create the FastAPI application instance
app = create_app()
