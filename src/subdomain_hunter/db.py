from typing import Generator
import logging

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session

from subdomain_hunter.config import get_settings
from subdomain_hunter.models.base import Base

logger = logging.getLogger(__name__)
settings = get_settings()

# Create database engine
engine = create_engine(
    settings.database_url,
    echo=settings.fastapi_debug,
    pool_pre_ping=True,  # Verify connections before using them
)

# Create session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db() -> Generator[Session, None, None]:
    """Get database session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db() -> None:
    """Initialize database tables."""
    try:
        Base.metadata.create_all(bind=engine)
        logger.info("Database initialized successfully")
    except Exception as e:
        logger.warning(f"Database initialization failed (continuing anyway): {str(e)}")
        logger.warning("Database features will be unavailable. For development, ensure PostgreSQL is running.")


def drop_db() -> None:
    """Drop all database tables."""
    try:
        Base.metadata.drop_all(bind=engine)
    except Exception as e:
        logger.warning(f"Failed to drop database: {str(e)}")
