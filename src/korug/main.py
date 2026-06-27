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
from limits import parse as parse_rate_limit
from sqlalchemy.orm import Session

from korug.config import get_settings
from korug.db import init_db, get_db, SessionLocal
from korug.audit import setup_audit_logger, log_audit_event, AuditEvent
from korug.api import domains, vulnerabilities, scans, export, alerts, settings, users, integrations, changes
from korug.auth_utils import (
    create_access_token,
    create_refresh_token,
    verify_token,
    get_current_user,
)
from korug.models import UserResponse
from korug.users import authenticate_user, get_user_by_username, record_login, seed_admin_user
from korug.token_blacklist import add_to_blacklist, is_blacklisted

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


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan context manager for startup and shutdown events."""
    # Startup
    logger.info("Starting up Körüg...")
    
    # Initialize audit logging
    setup_audit_logger("audit.log")
    
    init_db()
    logger.info("Database initialized")

    # Seed the initial admin account on first run (no-op if users already exist)
    try:
        db = SessionLocal()
        try:
            seed_admin_user(db)
        finally:
            db.close()
    except Exception as e:
        logger.error(f"Admin seeding skipped: {e}")

    # Reconcile scans orphaned by a previous restart. Background scan tasks do
    # not survive a process restart, so any scan still marked running/cancelling
    # is stale — mark it failed so the UI doesn't show a perpetual "Scanning…".
    try:
        from korug.models import ScanHistory
        db = SessionLocal()
        try:
            stale = db.query(ScanHistory).filter(
                ScanHistory.status.in_(("running", "cancelling"))
            ).all()
            for s in stale:
                s.status = "failed"
                s.error_message = "Interrupted by server restart"
            if stale:
                db.commit()
                logger.info("Reconciled %d orphaned scan(s) on startup", len(stale))
        finally:
            db.close()
    except Exception as e:
        logger.error(f"Scan reconciliation skipped: {e}")

    # Continuous monitoring: periodic re-discovery of all enabled domains.
    try:
        from korug.scheduler import start_scheduler
        start_scheduler()
    except Exception as e:
        logger.error(f"Scheduler start skipped: {e}")

    # Live Certificate Transparency monitoring (opt-in via ENABLE_CERTSTREAM).
    try:
        from korug.services.certstream_monitor import start_certstream
        start_certstream()
    except Exception as e:
        logger.error(f"Certstream monitor start skipped: {e}")

    yield

    # Shutdown
    logger.info("Shutting down Körüg...")
    try:
        from korug.scheduler import stop_scheduler
        stop_scheduler()
    except Exception as e:
        logger.error(f"Scheduler stop skipped: {e}")

    try:
        from korug.services.certstream_monitor import stop_certstream
        await stop_certstream()
    except Exception as e:
        logger.error(f"Certstream monitor stop skipped: {e}")


def create_app() -> FastAPI:
    """Create and configure FastAPI application."""
    app = FastAPI(
        title="Körüg",
        description="A comprehensive subdomain security monitoring tool",
        version="0.2.0",
        lifespan=lifespan,
        debug=app_settings.fastapi_debug,
    )
    
    # Initialize rate limiter. When REDIS_URL is set the counters live in Redis,
    # so limits are enforced consistently across all worker processes; otherwise
    # an in-memory store is used (single-process / local development only).
    if app_settings.enable_rate_limiting:
        limiter_kwargs = {"key_func": get_remote_address}
        if app_settings.redis_url:
            limiter_kwargs["storage_uri"] = app_settings.redis_url
            logger.info("Rate limiter: using Redis storage")
        else:
            logger.info("Rate limiter: using in-memory storage (single process)")
        limiter = Limiter(**limiter_kwargs)
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
    app.include_router(changes.router, prefix="/api/changes", tags=["changes"])
    app.include_router(export.router, prefix="/api/export", tags=["export"])
    app.include_router(alerts.router, prefix="/api/alerts", tags=["alerts"])
    app.include_router(settings.router, prefix="/api/settings", tags=["settings"])
    app.include_router(users.router, prefix="/api/users", tags=["users"])
    app.include_router(integrations.router, prefix="/api/integrations", tags=["integrations"])

    # Authentication endpoints
    @app.post("/api/auth/login", response_model=TokenResponse)
    async def login(request: LoginRequest, response: Response, db: Session = Depends(get_db)):
        """Login endpoint - validates credentials against the database and
        returns access and refresh tokens.

        SECURITY:
        - Credentials verified against bcrypt-hashed passwords in the database
        - Rate limited per IP+username to prevent brute force attacks
        - Generic error message to avoid username enumeration
        - Optional httpOnly cookies for token storage
        """
        # Apply rate limiting if enabled (per-username, brute-force protection).
        # slowapi's Limiter wraps a synchronous `limits` strategy at `.limiter`;
        # `hit()` returns False once the window is exhausted.
        if app.state.limiter:
            rate_item = parse_rate_limit(app_settings.login_rate_limit)
            if not app.state.limiter.limiter.hit(rate_item, "login", request.username):
                log_audit_event(
                    AuditEvent.LOGIN_FAILED,
                    user=request.username or "unknown",
                    status="failure",
                    details={"reason": "rate_limited"},
                )
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail="Too many login attempts. Please try again later.",
                )

        # Validate credentials against the database (bcrypt-hashed passwords).
        user = authenticate_user(db, request.username, request.password)
        if user is None:
            log_audit_event(
                AuditEvent.LOGIN_FAILED,
                user=request.username or "unknown",
                status="failure",
                details={"reason": "invalid_credentials"},
            )
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid username or password",
            )

        record_login(db, user)
        logger.info(f"User {user.username} logged in")

        log_audit_event(
            AuditEvent.LOGIN_SUCCESS,
            user=user.username,
            status="success",
        )

        access_token = create_access_token({"sub": user.username, "type": "access"})
        refresh_token = create_refresh_token({"sub": user.username})
        
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
    async def refresh_access_token(request: RefreshTokenRequest, response: Response, db: Session = Depends(get_db)):
        """Refresh access token using refresh token.

        SECURITY:
        - Validates refresh token type
        - Rejects revoked refresh tokens and deactivated/deleted users
        - Optional httpOnly cookie-based storage
        """
        try:
            payload = verify_token(request.refresh_token, token_type="refresh")

            # Reject refresh tokens that were revoked (e.g. via logout).
            if is_blacklisted(payload.get("jti")):
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Token has been revoked",
                )

            # Ensure the user still exists and is active.
            user = get_user_by_username(db, payload.get("sub"))
            if user is None or not user.is_active:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="User no longer exists or is inactive",
                )

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

        # Revoke the token by its jti until its natural expiry.
        try:
            token_payload = jwt.decode(
                token,
                app_settings.jwt_secret_key,
                algorithms=["HS256"]
            )
            jti = token_payload.get("jti")
            exp_time = token_payload.get("exp")
            if jti and exp_time:
                exp_datetime = datetime.fromtimestamp(exp_time, tz=timezone.utc)
                add_to_blacklist(jti, exp_datetime)
        except Exception as e:
            logger.warning(f"Could not revoke token on logout: {e}")
        
        logger.info(f"User {username} logged out")
        
        log_audit_event(
            AuditEvent.LOGOUT,
            user=username,
            status="success"
        )
        
        return {"message": "Logged out successfully"}

    @app.get("/api/auth/me", response_model=UserResponse)
    async def get_current_user_info(
        current_user: dict = Depends(get_current_user),
        db: Session = Depends(get_db),
    ):
        """Get the authenticated user's profile from the database."""
        user = get_user_by_username(db, current_user["sub"])
        if user is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found",
            )
        return user

    # Health check endpoint
    @app.get("/health")
    async def health_check():
        return {"status": "healthy"}

    return app


# Create the FastAPI application instance
app = create_app()
