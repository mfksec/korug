from typing import Generator
import logging

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session

from korug.config import get_settings
from korug.models.base import Base

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
    """Initialize database tables and apply lightweight column migrations."""
    try:
        Base.metadata.create_all(bind=engine)
        _add_missing_columns()
        logger.info("Database initialized successfully")
    except Exception as e:
        logger.warning(f"Database initialization failed (continuing anyway): {str(e)}")
        logger.warning("Database features will be unavailable. For development, ensure PostgreSQL is running.")


def _add_missing_columns() -> None:
    """Add columns present in the models but missing from existing tables.

    This project has no migration tool; new nullable columns added to a model
    won't appear in an already-created table. SQLite and PostgreSQL both support
    ``ALTER TABLE ... ADD COLUMN``, so we add any missing columns best-effort.
    Existing data is preserved.
    """
    from sqlalchemy import inspect, text

    inspector = inspect(engine)
    existing_tables = set(inspector.get_table_names())

    with engine.begin() as conn:
        for table in Base.metadata.sorted_tables:
            if table.name not in existing_tables:
                continue
            present = {col["name"] for col in inspector.get_columns(table.name)}
            for column in table.columns:
                if column.name in present:
                    continue
                try:
                    col_type = column.type.compile(dialect=engine.dialect)
                    conn.execute(text(
                        f'ALTER TABLE "{table.name}" ADD COLUMN "{column.name}" {col_type}'
                    ))
                    logger.info("Added missing column %s.%s", table.name, column.name)
                except Exception as exc:  # pragma: no cover - dialect quirks
                    logger.warning("Could not add column %s.%s: %s", table.name, column.name, exc)


def drop_db() -> None:
    """Drop all database tables."""
    try:
        Base.metadata.drop_all(bind=engine)
    except Exception as e:
        logger.warning(f"Failed to drop database: {str(e)}")
