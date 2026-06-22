"""Test configuration and fixtures."""
import os
import sys
from pathlib import Path

# Add src directory to path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

# Provide required settings for test imports
os.environ.setdefault("DATABASE_URL", "sqlite:///./test.db")
os.environ.setdefault("JWT_SECRET_KEY", "test-jwt-secret-key-with-32-plus-chars")
os.environ.setdefault("API_KEY", "test-api-key-with-32-plus-characters")
os.environ.setdefault("ALLOWED_ORIGINS", "http://localhost:3000")

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from subdomain_hunter.models.base import Base
from subdomain_hunter.db import get_db

# Use in-memory SQLite for testing
SQLALCHEMY_TEST_DATABASE_URL = "sqlite:///./test.db"


@pytest.fixture(scope="session")
def db_engine():
    """Create test database engine."""
    engine = create_engine(
        SQLALCHEMY_TEST_DATABASE_URL,
        connect_args={"check_same_thread": False},
    )
    Base.metadata.create_all(bind=engine)
    yield engine
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def db_session(db_engine):
    """Create test database session."""
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=db_engine)
    session = TestingSessionLocal()
    
    # Clear all tables before each test
    for table in reversed(Base.metadata.sorted_tables):
        session.execute(table.delete())
    session.commit()
    
    yield session
    session.close()


@pytest.fixture
def client(db_session):
    """Create test FastAPI client."""
    from fastapi.testclient import TestClient
    from subdomain_hunter.auth_utils import create_access_token
    from subdomain_hunter.main import app
    
    # Override get_db dependency
    def override_get_db():
        return db_session
    
    app.dependency_overrides[get_db] = override_get_db
    
    client = TestClient(app)
    token = create_access_token({"sub": "test-user"})
    client.headers.update({"Authorization": "Bearer " + token})
    yield client
    
    app.dependency_overrides.clear()
