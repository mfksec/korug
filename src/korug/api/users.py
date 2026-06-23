"""User management API endpoints (admin-gated) plus self-service profile/password."""
import logging
from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from korug.db import get_db
from korug.auth_utils import (
    get_current_user,
    require_role,
    hash_password,
    verify_password,
)
from korug.audit import log_audit_event, AuditEvent
from korug.models import (
    User,
    UserCreate,
    UserResponse,
    UserAdminUpdate,
    ProfileUpdate,
    PasswordChange,
    PasswordReset,
)
from korug.users import get_user_by_username, get_user_by_email

logger = logging.getLogger(__name__)
router = APIRouter()

VALID_ROLES = {"admin", "viewer"}


# ---------------------------------------------------------------------------
# Self-service: profile & password (any authenticated user)
# ---------------------------------------------------------------------------

@router.get("/me", response_model=UserResponse)
def get_my_profile(
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """Return the authenticated user's profile."""
    user = get_user_by_username(db, current_user["sub"])
    if not user:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "User not found")
    return user


@router.patch("/me", response_model=UserResponse)
def update_my_profile(
    update: ProfileUpdate,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """Update the authenticated user's own profile (email)."""
    user = get_user_by_username(db, current_user["sub"])
    if not user:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "User not found")

    existing = get_user_by_email(db, update.email)
    if existing and existing.id != user.id:
        raise HTTPException(status.HTTP_409_CONFLICT, "Email already in use")

    user.email = update.email
    db.add(user)
    db.commit()
    db.refresh(user)

    log_audit_event(
        AuditEvent.USER_UPDATED, user=current_user["sub"],
        resource_type="user", resource_id=user.id, details={"self": True},
    )
    return user


@router.post("/me/password", status_code=status.HTTP_204_NO_CONTENT)
def change_my_password(
    body: PasswordChange,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """Change the authenticated user's own password (verifies current password)."""
    user = get_user_by_username(db, current_user["sub"])
    if not user:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "User not found")

    if not verify_password(body.current_password, user.hashed_password):
        log_audit_event(
            AuditEvent.PASSWORD_CHANGED, user=current_user["sub"], status="failure",
            resource_type="user", resource_id=user.id, details={"reason": "bad_current_password"},
        )
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Current password is incorrect")

    user.hashed_password = hash_password(body.new_password)
    db.add(user)
    db.commit()

    log_audit_event(
        AuditEvent.PASSWORD_CHANGED, user=current_user["sub"],
        resource_type="user", resource_id=user.id,
    )
    return None


# ---------------------------------------------------------------------------
# Admin: user management
# ---------------------------------------------------------------------------

@router.get("/", response_model=List[UserResponse])
def list_users(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_role("admin")),
):
    """List all users (admin only)."""
    return db.query(User).order_by(User.id).offset(skip).limit(limit).all()


@router.post("/", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def create_user_endpoint(
    body: UserCreate,
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_role("admin")),
):
    """Create a new user (admin only)."""
    if body.role not in VALID_ROLES:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, f"role must be one of {sorted(VALID_ROLES)}")
    if get_user_by_username(db, body.username):
        raise HTTPException(status.HTTP_409_CONFLICT, "Username already exists")
    if get_user_by_email(db, body.email):
        raise HTTPException(status.HTTP_409_CONFLICT, "Email already exists")

    user = User(
        username=body.username,
        email=body.email,
        hashed_password=hash_password(body.password),
        role=body.role,
        is_active=True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    log_audit_event(
        AuditEvent.USER_CREATED, user=current_user["sub"],
        resource_type="user", resource_id=user.id,
        details={"username": user.username, "role": user.role},
    )
    return user


@router.get("/{user_id}", response_model=UserResponse)
def get_user(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_role("admin")),
):
    """Get a specific user (admin only)."""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "User not found")
    return user


@router.patch("/{user_id}", response_model=UserResponse)
def update_user(
    user_id: int,
    update: UserAdminUpdate,
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_role("admin")),
):
    """Update a user's email/role/active status (admin only)."""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "User not found")

    # Guard: don't let an admin lock themselves out (deactivate / demote self).
    is_self = user.username == current_user["sub"]
    if is_self and update.is_active is False:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "You cannot deactivate your own account")
    if is_self and update.role is not None and update.role != "admin":
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "You cannot change your own role")

    if update.role is not None:
        if update.role not in VALID_ROLES:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, f"role must be one of {sorted(VALID_ROLES)}")
        # Don't allow removing the last active admin.
        if user.role == "admin" and update.role != "admin" and _active_admin_count(db) <= 1:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "Cannot demote the last admin")
        user.role = update.role

    if update.email is not None:
        existing = get_user_by_email(db, update.email)
        if existing and existing.id != user.id:
            raise HTTPException(status.HTTP_409_CONFLICT, "Email already in use")
        user.email = update.email

    if update.is_active is not None:
        if user.is_active and not update.is_active and user.role == "admin" and _active_admin_count(db) <= 1:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "Cannot deactivate the last admin")
        user.is_active = update.is_active

    db.add(user)
    db.commit()
    db.refresh(user)

    log_audit_event(
        AuditEvent.USER_UPDATED, user=current_user["sub"],
        resource_type="user", resource_id=user.id,
        details=update.dict(exclude_unset=True),
    )
    return user


@router.post("/{user_id}/password", status_code=status.HTTP_204_NO_CONTENT)
def reset_user_password(
    user_id: int,
    body: PasswordReset,
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_role("admin")),
):
    """Reset another user's password (admin only)."""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "User not found")

    user.hashed_password = hash_password(body.new_password)
    db.add(user)
    db.commit()

    log_audit_event(
        AuditEvent.PASSWORD_RESET, user=current_user["sub"],
        resource_type="user", resource_id=user.id,
        details={"username": user.username},
    )
    return None


@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_user(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_role("admin")),
):
    """Delete a user (admin only). Cannot delete self or the last admin."""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "User not found")

    if user.username == current_user["sub"]:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "You cannot delete your own account")
    if user.role == "admin" and _active_admin_count(db) <= 1:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Cannot delete the last admin")

    log_audit_event(
        AuditEvent.USER_DELETED, user=current_user["sub"],
        resource_type="user", resource_id=user.id,
        details={"username": user.username},
    )
    db.delete(user)
    db.commit()
    return None


def _active_admin_count(db: Session) -> int:
    return db.query(User).filter(User.role == "admin", User.is_active.is_(True)).count()
