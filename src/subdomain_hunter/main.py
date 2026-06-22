import logging
import os
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from typing import Optional
import jwt

from fastapi import FastAPI, HTTPException, Request, status, Depends, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.security import HTTPBearer
from pydantic import BaseModel
from slowapi import Limiter
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

from subdomain_hunter.config import get_settings
from subdomain_hunter.db import init_db
from subdomain_hunter.audit import setup_audit_logger, log_audit_event, AuditEvent
from subdomain_hunter.api import domains, vulnerabilities, scans, export, alerts, settings
from subdomain_hunter.auth_utils import (
    create_access_token,
    create_refresh_token,
    verify_token,
    get_current_user,
    hash_password,
    verify_password,
)
from subdomain_hunter.token_blacklist import add_to_blacklist

logger = logging.getLogger(__name__)
app_settings = get_settings()


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
    
    # Initialize audit logging
    setup_audit_logger("audit.log")
    
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
        debug=app_settings.fastapi_debug,
    )
    
    # Initialize rate limiter
    if app_settings.enable_rate_limiting:
        limiter = Limiter(key_func=get_remote_address)
        app.state.limiter = limiter
        
        @app.exception_handler(RateLimitExceeded)
        async def rate_limit_exception_handler(request, exc):
            return JSONResponse(
                status_code=429,
                content={"detail": "Rate limit exceeded. Please try again later."},
            )
    else:
        app.state.limiter = None

    # Parse CORS origins from configuration
    allowed_origins = [
        origin.strip() for origin in app_settings.allowed_origins.split(",")
    ]

    # Add CORS middleware with explicit origins
    app.add_middleware(
        CORSMiddleware,
        allow_origins=allowed_origins,  # Explicit list only
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],  # Restrict methods
        allow_headers=["Content-Type", "Authorization"],  # Restrict headers
        max_age=600,  # Cache preflight for 10 minutes
    )
    
    # Add security headers middleware
    @app.middleware("http")
    async def add_security_headers(request, call_next):
        """Add security headers to all responses."""
        response = await call_next(request)
        
        # Prevent clickjacking
        response.headers["X-Frame-Options"] = "DENY"
        
        # Prevent MIME type sniffing
        response.headers["X-Content-Type-Options"] = "nosniff"
        
        # Enable XSS protection
        response.headers["X-XSS-Protection"] = "1; mode=block"
        
        # Referrer policy
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        
        # Permissions policy (formerly Feature-Policy)
        response.headers["Permissions-Policy"] = "geolocation=(), microphone=(), camera=()"
        
        # Content Security Policy - strict XSS protection
        # Note: Adjust 'script-src' if you need inline scripts or specific CDNs
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; "
            "script-src 'self' 'unsafe-inline'; "
            "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; "
            "font-src 'self' https://fonts.gstatic.com; "
            "img-src 'self' data: https:; "
            "connect-src 'self' localhost:*; "
            "form-action 'self'; "
            "frame-ancestors 'none'; "
            "base-uri 'self'; "
            "upgrade-insecure-requests"
        )
        
        return response

    # Include routers with authentication
    app.include_router(domains.router, prefix="/api/domains", tags=["domains"])
    app.include_router(vulnerabilities.router, prefix="/api/vulnerabilities", tags=["vulnerabilities"])
    app.include_router(scans.router, prefix="/api/scans", tags=["scans"])
    app.include_router(export.router, prefix="/api/export", tags=["export"])
    app.include_router(alerts.router, prefix="/api/alerts", tags=["alerts"])
    app.include_router(settings.router, prefix="/api/settings", tags=["settings"])

    # Authentication endpoints
    @app.post("/api/auth/login", response_model=TokenResponse)
    async def login(request: LoginRequest, response: Response):
        """Login endpoint - returns access and refresh tokens.
        
        SECURITY: 
        - Rate limited to prevent brute force attacks
        - Optional httpOnly cookies for token storage
        """
        # Apply rate limiting if enabled
        if app.state.limiter:
            await app.state.limiter.hit(
                f"login_{request.username}",
                app_settings.login_rate_limit
            )
        
        # For demo: accept any non-empty credentials
        # In production: validate against user database with password hashing
        if not request.username or not request.password:
            log_audit_event(
                AuditEvent.LOGIN_FAILED,
                user=request.username or "unknown",
                status="failure",
                details={"reason": "empty_credentials"}
            )
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid username or password",
            )
        
        # TODO: Replace with database user lookup and verify_password() call
        # user = db.query(User).filter(User.username == request.username).first()
        # if not user or not verify_password(request.password, user.hashed_password):
        #     log_audit_event(AuditEvent.LOGIN_FAILED, user=request.username, status="failure")
        #     raise HTTPException(status_code=401, detail="Invalid username or password")
        
        logger.info(f"User {request.username} logged in")
        
        log_audit_event(
            AuditEvent.LOGIN_SUCCESS,
            user=request.username,
            status="success"
        )
        
        access_token = create_access_token({"sub": request.username, "type": "access"})
        refresh_token = create_refresh_token({"sub": request.username})
        
        # Option 1: Use httpOnly cookies (recommended for production)
        if app_settings.use_httponly_cookies:
            response.set_cookie(
                "access_token",
                access_token,
                httponly=True,
                secure=app_settings.cookie_secure,
                samesite="Strict",
                max_age=3600  # 1 hour
            )
            response.set_cookie(
                "refresh_token",
                refresh_token,
                httponly=True,
                secure=app_settings.cookie_secure,
                samesite="Strict",
                max_age=604800  # 7 days
            )
        
        # Return tokens in body (always, for frontend compatibility)
        return {
            "access_token": access_token,
            "refresh_token": refresh_token,
        }

    @app.post("/api/auth/refresh")
    async def refresh_access_token(request: RefreshTokenRequest, response: Response):
        """Refresh access token using refresh token.
        
        SECURITY:
        - Validates refresh token type
        - Optional httpOnly cookie-based storage
        """
        try:
            payload = verify_token(request.refresh_token, token_type="refresh")
            
            log_audit_event(
                AuditEvent.TOKEN_REFRESH,
                user=payload.get("sub"),
                status="success"
            )
            
            access_token = create_access_token({"sub": payload["sub"], "type": "access"})
            
            # Option 1: Use httpOnly cookies
            if app_settings.use_httponly_cookies:
                response.set_cookie(
                    "access_token",
                    access_token,
                    httponly=True,
                    secure=app_settings.cookie_secure,
                    samesite="Strict",
                    max_age=3600  # 1 hour
                )
            
            # Return token in body (always, for frontend compatibility)
            return {"access_token": access_token}
        except HTTPException:
            log_audit_event(
                AuditEvent.TOKEN_REFRESH_FAILED,
                user="unknown",
                status="failure",
                details={"reason": "invalid_token"}
            )
            raise
        except Exception as e:
            logger.error(f"Token refresh failed: {str(e)}")
            log_audit_event(
                AuditEvent.TOKEN_REFRESH_FAILED,
                user="unknown",
                status="failure",
                details={"reason": "exception", "error": str(e)[:100]}
            )
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid refresh token",
            )

    @app.post("/api/auth/logout")
    async def logout(request: Request, current_user: dict = Depends(get_current_user)):
        """Logout endpoint - invalidates token by adding to blacklist.
        
        SECURITY:
        - Token is added to revocation blacklist
        - Future attempts to use this token will be rejected
        - Solves client-side expiry check vulnerability
        """
        username = current_user['sub']
        auth_header = request.headers.get("authorization", "")
        token = auth_header.removeprefix("Bearer ").strip()
        
        # Extract token expiration and add to blacklist
        try:
            token_payload = jwt.decode(
                token,
                app_settings.jwt_secret_key,
                algorithms=["HS256"]
            )
            exp_time = token_payload.get('exp')
            if exp_time:
                exp_datetime = datetime.fromtimestamp(exp_time, tz=timezone.utc)
                # Add token to blacklist until expiration
                add_to_blacklist(token, exp_datetime)
        except Exception as e:
            logger.warning(f"Could not extract token expiry for blacklist: {e}")
        
        logger.info(f"User {username} logged out")
        
        log_audit_event(
            AuditEvent.LOGOUT,
            user=username,
            status="success"
        )
        
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
