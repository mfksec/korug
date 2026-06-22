import logging
from contextlib import asynccontextmanager
from typing import Optional

from fastapi import FastAPI, HTTPException, status, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from subdomain_hunter.config import get_settings
from subdomain_hunter.db import init_db
from subdomain_hunter.api import domains, vulnerabilities, scans, export
from subdomain_hunter.auth_utils import (
    create_access_token,
    create_refresh_token,
    verify_token,
    get_current_user,
)

logger = logging.getLogger(__name__)
settings = get_settings()


# Request/Response Models for Auth
class LoginRequest(BaseModel):
    username: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class RefreshTokenRequest(BaseModel):
    refresh_token: str


class UserResponse(BaseModel):
    id: int
    email: str
    role: str = "admin"


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
        allow_origins=[
            "http://localhost:5173",
            "http://localhost:3000",
            "http://localhost:8000",
            "http://127.0.0.1:5173",
            "http://127.0.0.1:3000",
            "*",  # TODO: Restrict in production
        ],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Include routers
    app.include_router(domains.router, prefix="/api/domains", tags=["domains"])
    app.include_router(vulnerabilities.router, prefix="/api/vulnerabilities", tags=["vulnerabilities"])
    app.include_router(scans.router, prefix="/api/scans", tags=["scans"])
    app.include_router(export.router, prefix="/api/export", tags=["export"])

    # Authentication endpoints
    @app.post("/api/auth/login", response_model=TokenResponse)
    async def login(request: LoginRequest):
        """Login endpoint - returns access and refresh tokens."""
        # Basic validation - in production, validate against user database
        if not request.username or not request.password:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid credentials",
            )
        
        access_token = create_access_token({"sub": request.username, "type": "access"})
        refresh_token = create_refresh_token({"sub": request.username})
        
        return {
            "access_token": access_token,
            "refresh_token": refresh_token,
        }

    @app.post("/api/auth/refresh")
    async def refresh_access_token(request: RefreshTokenRequest):
        """Refresh access token using refresh token."""
        try:
            payload = verify_token(request.refresh_token)
            if payload.get("type") != "refresh":
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid token type",
                )
            
            access_token = create_access_token({"sub": payload["sub"], "type": "access"})
            return {"access_token": access_token}
        except HTTPException:
            raise
        except Exception:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid refresh token",
            )

    @app.post("/api/auth/logout")
    async def logout(current_user: dict = Depends(get_current_user)):
        """Logout endpoint."""
        # Token is invalidated on client side by removing from localStorage
        return {"message": "Logged out successfully"}

    @app.get("/api/auth/me", response_model=UserResponse)
    async def get_current_user_info(current_user: dict = Depends(get_current_user)):
        """Get current user info."""
        return {
            "id": 1,
            "email": current_user.get("sub", "user@example.com"),
            "role": "admin",
        }

    # Health check endpoint
    @app.get("/health")
    async def health_check():
        return {"status": "healthy"}

    return app


# Create the FastAPI application instance
app = create_app()
