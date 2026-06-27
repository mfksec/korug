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
# Redis: use in-memory fallback for tests (REDIS_URL not set)
os.environ.pop("REDIS_URL", None)
# Admin seeding disabled for tests (will create users explicitly)
os.environ.setdefault("ADMIN_USERNAME", "")
# Auto-discovery disabled in tests so domain CRUD doesn't perform network I/O.
os.environ.setdefault("ENABLE_AUTO_DISCOVERY", "false")
# Network-bound scan steps disabled in tests (CVE lookup, crt.sh certificates).
os.environ.setdefault("ENABLE_AUTO_CVE", "false")
os.environ.setdefault("ENABLE_CVE_SCAN", "false")
os.environ.setdefault("ENABLE_CERT_MONITORING", "false")
# Keep integration config hermetic: a developer .env may carry a real Slack
# webhook / SMTP creds, which would otherwise leak into the "defaults empty"
# tests. Env vars take precedence over the .env file in pydantic-settings, so
# blanking them here isolates the suite from local secrets.
os.environ["SLACK_WEBHOOK_URL"] = ""
os.environ["SLACK_ENABLED"] = "false"

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from datetime import datetime

from korug.models.base import Base
from korug.models import User
from korug.db import get_db
from korug.auth_utils import hash_password, create_access_token, create_refresh_token

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
def test_user(db_session) -> User:
    """Create a test user for authentication tests."""
    user = User(
        username="testuser",
        email="testuser@example.com",
        hashed_password=hash_password("testpassword123"),
        role="admin",
        is_active=True,
        created_at=datetime.utcnow(),
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture
def test_user_viewer(db_session) -> User:
    """Create a test viewer user for RBAC tests."""
    user = User(
        username="vieweruser",
        email="viewer@example.com",
        hashed_password=hash_password("viewerpass123"),
        role="viewer",
        is_active=True,
        created_at=datetime.utcnow(),
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture
def access_token(test_user):
    """Generate an access token for the test user."""
    return create_access_token({"sub": test_user.username, "type": "access"})


@pytest.fixture
def refresh_token(test_user):
    """Generate a refresh token for the test user."""
    return create_refresh_token({"sub": test_user.username})


@pytest.fixture
def client(db_session, test_user, access_token):
    """Create test FastAPI client with authentication."""
    from fastapi.testclient import TestClient
    from korug.main import app
    import korug.token_blacklist as token_blacklist_module

    # Override get_db dependency
    def override_get_db():
        return db_session
    
    app.dependency_overrides[get_db] = override_get_db

    # Clear the token blacklist before each test to prevent state bleed
    with token_blacklist_module._lock:
        token_blacklist_module._blacklist.clear()
    
    client = TestClient(app)
    # Add authentication token by default
    client.headers.update({"Authorization": f"Bearer {access_token}"})
    yield client
    
    app.dependency_overrides.clear()


@pytest.fixture
def authenticated_client(client, access_token):
    """Create an authenticated test client with access token (alias for client)."""
    return client

