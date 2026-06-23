"""Settings and audit log API endpoints."""
import hashlib
import logging
import secrets
from typing import List
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from korug.db import get_db
from korug.auth_utils import get_current_user
from korug.models import ApiKey, UserSetting, AuditLog

logger = logging.getLogger(__name__)
router = APIRouter()


# Schemas
class AuditLogResponse(BaseModel):
    id: int
    user_id: int = 0
    user: str | None = None
    action: str
    resource: str | None = None
    details: str | None = None
    ip_address: str | None = None
    user_agent: str | None = None
    timestamp: str
    status: str = "success"


class UserSettings(BaseModel):
    theme: str = "light"  # light or dark
    notifications_enabled: bool = True
    email_alerts: bool = True
    scan_frequency: str = "daily"  # daily, weekly, monthly
    export_format: str = "json"  # json, csv, pdf


class UserSettingsResponse(BaseModel):
    user_id: int
    settings: UserSettings
    updated_at: str


class APIKeyResponse(BaseModel):
    id: int
    name: str
    key: str  # full key on creation, masked thereafter
    created_at: str
    last_used: str | None = None
    is_active: bool = True


class APIKeyCreate(BaseModel):
    name: str


# Settings Endpoints

@router.get("/settings/user", response_model=UserSettingsResponse)
def get_user_settings(
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """Get current user's settings."""
    user_id = current_user.get("sub", "user")
    record = db.query(UserSetting).filter(UserSetting.user_id == user_id).first()

    if record:
        return {
            "user_id": record.id,
            "settings": UserSettings(
                theme=record.theme,
                notifications_enabled=record.notifications_enabled,
                email_alerts=record.email_alerts,
                scan_frequency=record.scan_frequency,
                export_format=record.export_format,
            ).dict(),
            "updated_at": (record.updated_at or datetime.utcnow()).isoformat() + "Z",
        }

    # No stored settings yet - return defaults without persisting.
    return {
        "user_id": 0,
        "settings": UserSettings().dict(),
        "updated_at": datetime.utcnow().isoformat() + "Z",
    }


@router.post("/settings/user", response_model=UserSettingsResponse)
def update_user_settings(
    settings: UserSettings,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """Create or update the current user's settings."""
    user_id = current_user.get("sub", "user")
    record = db.query(UserSetting).filter(UserSetting.user_id == user_id).first()

    if not record:
        record = UserSetting(user_id=user_id)

    record.theme = settings.theme
    record.notifications_enabled = settings.notifications_enabled
    record.email_alerts = settings.email_alerts
    record.scan_frequency = settings.scan_frequency
    record.export_format = settings.export_format

    db.add(record)
    db.commit()
    db.refresh(record)

    return {
        "user_id": record.id,
        "settings": settings.dict(),
        "updated_at": (record.updated_at or datetime.utcnow()).isoformat() + "Z",
    }


# API Keys Endpoints

@router.get("/apikeys", response_model=List[APIKeyResponse])
def list_api_keys(
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """List all API keys for the current user."""
    user_id = current_user.get("sub", "user")
    keys = db.query(ApiKey).filter(ApiKey.user_id == user_id).all()
    return [
        {
            "id": k.id,
            "name": k.name,
            "key": k.key_display,
            "created_at": k.created_at.isoformat() + "Z" if k.created_at else "",
            "last_used": k.last_used.isoformat() + "Z" if k.last_used else None,
            "is_active": k.is_active,
        }
        for k in keys
    ]


@router.post("/apikeys", response_model=APIKeyResponse)
def create_api_key(
    request: APIKeyCreate,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """Create a new API key. The full secret is returned only once."""
    user_id = current_user.get("sub", "user")

    # Generate a real secret; persist only its hash and a masked display value.
    secret = f"sk-{secrets.token_hex(24)}"
    key_hash = hashlib.sha256(secret.encode()).hexdigest()
    key_display = f"sk-****{secret[-8:]}"

    record = ApiKey(
        user_id=user_id,
        name=request.name,
        key_hash=key_hash,
        key_display=key_display,
    )
    db.add(record)
    db.commit()
    db.refresh(record)

    return {
        "id": record.id,
        "name": record.name,
        "key": secret,  # shown once at creation time
        "created_at": record.created_at.isoformat() + "Z" if record.created_at else "",
        "last_used": None,
        "is_active": record.is_active,
    }


@router.delete("/apikeys/{key_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_api_key(
    key_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """Delete an API key."""
    user_id = current_user.get("sub", "user")
    record = db.query(ApiKey).filter(
        ApiKey.id == key_id, ApiKey.user_id == user_id
    ).first()
    if not record:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"API key with id {key_id} not found",
        )

    db.delete(record)
    db.commit()
    return None


@router.post("/apikeys/{key_id}/revoke", response_model=APIKeyResponse)
def revoke_api_key(
    key_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """Revoke an API key (disable without deleting)."""
    user_id = current_user.get("sub", "user")
    record = db.query(ApiKey).filter(
        ApiKey.id == key_id, ApiKey.user_id == user_id
    ).first()
    if not record:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"API key with id {key_id} not found",
        )

    record.is_active = False
    db.add(record)
    db.commit()
    db.refresh(record)

    return {
        "id": record.id,
        "name": record.name,
        "key": record.key_display,
        "created_at": record.created_at.isoformat() + "Z" if record.created_at else "",
        "last_used": record.last_used.isoformat() + "Z" if record.last_used else None,
        "is_active": record.is_active,
    }


# Audit Log Endpoints

def _scope_to_user(query, current_user: dict):
    """Restrict an AuditLog query to the caller's own events.

    Admins retain the global view (operational/security oversight); every other
    role only ever sees the audit events attributed to their own username. This
    prevents cross-user activity disclosure (IDOR).
    """
    if current_user.get("role") != "admin":
        query = query.filter(AuditLog.user == current_user.get("sub", "user"))
    return query


def _serialize_audit(log: AuditLog) -> dict:
    """Map an AuditLog ORM row into the API response shape."""
    resource = log.resource_type
    if resource and log.resource_id:
        resource = f"{resource}:{log.resource_id}"
    return {
        "id": log.id,
        "user_id": 0,
        "user": log.user,
        "action": log.event,
        "resource": resource,
        "details": log.details,
        "ip_address": None,
        "user_agent": None,
        "timestamp": log.timestamp.isoformat() + "Z" if log.timestamp else "",
        "status": log.status,
    }


@router.get("/audit-logs", response_model=List[AuditLogResponse])
def list_audit_logs(
    action: str | None = None,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """List real audit log entries for the caller, most recent first."""
    query = _scope_to_user(db.query(AuditLog), current_user)
    if action:
        query = query.filter(AuditLog.event == action)

    logs = query.order_by(AuditLog.timestamp.desc()).limit(limit).all()
    return [_serialize_audit(log) for log in logs]


@router.get("/audit-logs/stats/summary")
def get_audit_stats(
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """Get audit log statistics derived from real events, scoped to the caller."""
    logs = _scope_to_user(db.query(AuditLog), current_user).all()

    by_action: dict = {}
    for log in logs:
        by_action[log.event] = by_action.get(log.event, 0) + 1

    last_login_row = (
        _scope_to_user(db.query(AuditLog), current_user)
        .filter(AuditLog.event == "login_success")
        .order_by(AuditLog.timestamp.desc())
        .first()
    )
    last_login = (
        last_login_row.timestamp.isoformat() + "Z"
        if last_login_row and last_login_row.timestamp
        else None
    )

    active_keys = db.query(ApiKey).filter(
        ApiKey.user_id == current_user.get("sub", "user"),
        ApiKey.is_active.is_(True),
    ).count()

    return {
        "total_actions": len(logs),
        "by_action": by_action,
        "last_login": last_login,
        "api_keys_active": active_keys,
    }


@router.get("/audit-logs/{log_id}", response_model=AuditLogResponse)
def get_audit_log(
    log_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """Get a specific audit log entry owned by the caller."""
    log = _scope_to_user(
        db.query(AuditLog).filter(AuditLog.id == log_id), current_user
    ).first()
    if not log:
        # 404 (not 403) so a non-owner cannot probe which log ids exist.
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Audit log with id {log_id} not found",
        )
    return _serialize_audit(log)
