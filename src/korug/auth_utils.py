"""JWT authentication utilities with password hashing."""
import uuid
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
import bcrypt
import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer
from sqlalchemy.orm import Session

from korug.config import get_settings
from korug.db import get_db
from korug.models import User
from korug.token_blacklist import is_blacklisted

settings = get_settings()
security = HTTPBearer()

# bcrypt only considers the first 72 bytes of a password. We truncate
# explicitly (consistently for hash and verify) so longer inputs don't raise.
_BCRYPT_MAX_BYTES = 72


def _to_bcrypt_bytes(password: str) -> bytes:
    return password.encode("utf-8")[:_BCRYPT_MAX_BYTES]


def hash_password(password: str) -> str:
    """Hash a password using bcrypt and return the encoded hash string."""
    return bcrypt.hashpw(_to_bcrypt_bytes(password), bcrypt.gensalt()).decode("utf-8")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against its bcrypt hash (constant-time)."""
    try:
        return bcrypt.checkpw(_to_bcrypt_bytes(plain_password), hashed_password.encode("utf-8"))
    except (ValueError, TypeError):
        return False


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """Create JWT access token with proper secret and type validation."""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(hours=1)  # Shorter default expiry
    
    to_encode.update({
        "exp": expire,
        "type": "access",  # Explicit type marker
        "iat": datetime.utcnow(),
        "jti": uuid.uuid4().hex,  # Unique id for revocation
    })
    try:
        # Use configured secret - NO FALLBACK
        encoded_jwt = jwt.encode(
            to_encode, 
            settings.jwt_secret_key, 
            algorithm="HS256"
        )
        return encoded_jwt
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Token creation failed"
        )


def create_refresh_token(data: dict) -> str:
    """Create JWT refresh token with type marker."""
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(days=7)
    to_encode.update({
        "exp": expire,
        "type": "refresh",  # Type marker for validation
        "iat": datetime.utcnow(),
        "jti": uuid.uuid4().hex,  # Unique id for revocation
    })
    try:
        # Use configured secret - NO FALLBACK
        encoded_jwt = jwt.encode(
            to_encode, 
            settings.jwt_secret_key, 
            algorithm="HS256"
        )
        return encoded_jwt
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Token creation failed"
        )


def verify_token(token: str, token_type: str = "access") -> Dict[str, Any]:
    """Verify JWT token with type validation."""
    try:
        payload = jwt.decode(
            token, 
            settings.jwt_secret_key, 
            algorithms=["HS256"]
        )
        
        # Enforce token type
        if payload.get("type") != token_type:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=f"Invalid token type",
            )
        
        return payload
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token expired",
        )
    except jwt.InvalidTokenError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token",
        )


async def get_current_user(
    credentials=Depends(security),
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    """Resolve the current user from a bearer token.

    Performs, in order: signature/type validation, revocation (jti) check, and a
    database lookup to confirm the user still exists and is active. Returns the
    token payload enriched with ``user_id`` and ``role`` from the database. The
    ``sub`` claim (username) is preserved for backward compatibility with
    existing route handlers.
    """
    token = credentials.credentials

    payload = verify_token(token, token_type="access")

    # Reject tokens revoked via logout (checked by jti)
    if is_blacklisted(payload.get("jti")):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has been revoked",
        )

    username = payload.get("sub")
    user = db.query(User).filter(User.username == username).first()
    if user is None or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User no longer exists or is inactive",
        )

    payload["user_id"] = user.id
    payload["role"] = user.role
    return payload


def require_role(*roles: str):
    """Dependency factory enforcing that the current user has one of ``roles``."""

    async def _checker(current_user: Dict[str, Any] = Depends(get_current_user)) -> Dict[str, Any]:
        if current_user.get("role") not in roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permissions",
            )
        return current_user

    return _checker

