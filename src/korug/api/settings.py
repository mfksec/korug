"""Settings and audit log API endpoints."""
import logging
from typing import List
from datetime import datetime
from enum import Enum

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from korug.db import get_db
from korug.auth_utils import get_current_user

logger = logging.getLogger(__name__)
router = APIRouter()


# Models
class AuditAction(str, Enum):
    LOGIN = "login"
    LOGOUT = "logout"
    CREATE_DOMAIN = "create_domain"
    DELETE_DOMAIN = "delete_domain"
    RUN_SCAN = "run_scan"
    EXPORT_DATA = "export_data"
    CREATE_API_KEY = "create_api_key"
    DELETE_API_KEY = "delete_api_key"
    UPDATE_SETTINGS = "update_settings"
    OTHER = "other"


class AuditLogResponse(BaseModel):
    id: int
    user_id: int
    action: AuditAction
    resource: str | None = None
    details: str | None = None
    ip_address: str | None = None
    user_agent: str | None = None
    timestamp: str
    status: str = "success"  # success, failure

    class Config:
        from_attributes = True


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
    key: str  # Only first/last 8 chars shown in responses
    created_at: str
    last_used: str | None = None
    is_active: bool = True


class APIKeyCreate(BaseModel):
    name: str


# Mock data
MOCK_API_KEYS = [
    {
        "id": 1,
        "user_id": 1,
        "name": "Development Key",
        "key": "sk-****2a8f9e3b7c1d4",
        "created_at": "2026-06-01T10:00:00Z",
        "last_used": "2026-06-22T14:30:00Z",
        "is_active": True,
    },
    {
        "id": 2,
        "user_id": 1,
        "name": "CI/CD Integration",
        "key": "sk-****5x2m7k9p3q1r",
        "created_at": "2026-05-15T09:00:00Z",
        "last_used": "2026-06-20T08:00:00Z",
        "is_active": True,
    },
]

MOCK_AUDIT_LOGS = [
    {
        "id": 1,
        "user_id": 1,
        "action": "login",
        "resource": None,
        "details": "User logged in from dashboard",
        "ip_address": "192.168.1.100",
        "user_agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)",
        "timestamp": "2026-06-22T15:30:00Z",
        "status": "success",
    },
    {
        "id": 2,
        "user_id": 1,
        "action": "run_scan",
        "resource": "example.com",
        "details": "Initiated subdomain scan",
        "ip_address": "192.168.1.100",
        "user_agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)",
        "timestamp": "2026-06-22T14:00:00Z",
        "status": "success",
    },
    {
        "id": 3,
        "user_id": 1,
        "action": "export_data",
        "resource": "vulnerabilities",
        "details": "Exported vulnerability report (CSV)",
        "ip_address": "192.168.1.100",
        "user_agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)",
        "timestamp": "2026-06-21T10:30:00Z",
        "status": "success",
    },
    {
        "id": 4,
        "user_id": 1,
        "action": "create_api_key",
        "resource": "CI/CD Integration",
        "details": "Created new API key",
        "ip_address": "192.168.1.100",
        "user_agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)",
        "timestamp": "2026-06-15T09:00:00Z",
        "status": "success",
    },
]

MOCK_SETTINGS = {
    "1": {
        "user_id": 1,
        "settings": {
            "theme": "dark",
            "notifications_enabled": True,
            "email_alerts": True,
            "scan_frequency": "daily",
            "export_format": "json",
        },
        "updated_at": "2026-06-20T12:00:00Z",
    }
}


# Settings Endpoints

@router.get("/settings/user", response_model=UserSettingsResponse)
def get_user_settings(current_user: dict = Depends(get_current_user)):
    """Get current user's settings."""
    user_id = current_user.get("sub", "user")
    
    if user_id in MOCK_SETTINGS:
        return MOCK_SETTINGS[user_id]
    
    # Return default settings
    return {
        "user_id": 1,
        "settings": UserSettings().dict(),
        "updated_at": datetime.utcnow().isoformat() + "Z",
    }


@router.post("/settings/user", response_model=UserSettingsResponse)
def update_user_settings(
    settings: UserSettings,
    current_user: dict = Depends(get_current_user),
):
    """Update current user's settings."""
    user_id = "1"  # Simplified for now
    
    MOCK_SETTINGS[user_id] = {
        "user_id": 1,
        "settings": settings.dict(),
        "updated_at": datetime.utcnow().isoformat() + "Z",
    }
    
    # Log the update
    _log_audit_action(1, AuditAction.UPDATE_SETTINGS, "user_settings", "Updated user settings")
    
    return MOCK_SETTINGS[user_id]


# API Keys Endpoints

@router.get("/apikeys", response_model=List[APIKeyResponse])
def list_api_keys(current_user: dict = Depends(get_current_user)):
    """List all API keys for the current user."""
    return MOCK_API_KEYS


@router.post("/apikeys", response_model=APIKeyResponse)
def create_api_key(
    request: APIKeyCreate,
    current_user: dict = Depends(get_current_user),
):
    """Create a new API key."""
    new_id = max([k["id"] for k in MOCK_API_KEYS]) + 1 if MOCK_API_KEYS else 1
    
    # Generate a mock key (in production, generate a real secure key)
    import secrets
    key = f"sk-{secrets.token_hex(16)}"
    
    new_key = {
        "id": new_id,
        "user_id": 1,
        "name": request.name,
        "key": f"sk-****{key[-8:]}",  # Show only last 8 chars
        "created_at": datetime.utcnow().isoformat() + "Z",
        "last_used": None,
        "is_active": True,
    }
    
    MOCK_API_KEYS.append(new_key)
    
    # Log the action
    _log_audit_action(1, AuditAction.CREATE_API_KEY, request.name, "Created new API key")
    
    return new_key


@router.delete("/apikeys/{key_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_api_key(key_id: int, current_user: dict = Depends(get_current_user)):
    """Delete an API key."""
    for i, key in enumerate(MOCK_API_KEYS):
        if key["id"] == key_id:
            key_name = key["name"]
            MOCK_API_KEYS.pop(i)
            _log_audit_action(1, AuditAction.DELETE_API_KEY, key_name, "Deleted API key")
            return None
    
    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail=f"API key with id {key_id} not found",
    )


@router.post("/apikeys/{key_id}/revoke", response_model=APIKeyResponse)
def revoke_api_key(key_id: int, current_user: dict = Depends(get_current_user)):
    """Revoke an API key (disable without deleting)."""
    for key in MOCK_API_KEYS:
        if key["id"] == key_id:
            key["is_active"] = False
            _log_audit_action(1, AuditAction.DELETE_API_KEY, key["name"], "Revoked API key")
            return key
    
    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail=f"API key with id {key_id} not found",
    )


# Audit Log Endpoints

@router.get("/audit-logs", response_model=List[AuditLogResponse])
def list_audit_logs(
    action: AuditAction | None = None,
    limit: int = 100,
    current_user: dict = Depends(get_current_user),
):
    """List audit logs for the current user."""
    logs = MOCK_AUDIT_LOGS.copy()
    
    if action:
        logs = [log for log in logs if log["action"] == action]
    
    # Return most recent first
    logs.sort(key=lambda x: x["timestamp"], reverse=True)
    
    return logs[:limit]


@router.get("/audit-logs/{log_id}", response_model=AuditLogResponse)
def get_audit_log(log_id: int, current_user: dict = Depends(get_current_user)):
    """Get a specific audit log entry."""
    for log in MOCK_AUDIT_LOGS:
        if log["id"] == log_id:
            return log
    
    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail=f"Audit log with id {log_id} not found",
    )


@router.get("/audit-logs/stats/summary")
def get_audit_stats(current_user: dict = Depends(get_current_user)):
    """Get audit log statistics."""
    logs = MOCK_AUDIT_LOGS
    
    actions = {}
    for log in logs:
        action = log["action"]
        actions[action] = actions.get(action, 0) + 1
    
    return {
        "total_actions": len(logs),
        "by_action": actions,
        "last_login": "2026-06-22T15:30:00Z",
        "api_keys_active": len([k for k in MOCK_API_KEYS if k["is_active"]]),
    }


# Helper function

def _log_audit_action(
    user_id: int,
    action: AuditAction,
    resource: str | None = None,
    details: str | None = None,
    ip_address: str | None = None,
    status_code: str = "success",
):
    """Helper to add an audit log entry."""
    new_id = max([log["id"] for log in MOCK_AUDIT_LOGS]) + 1 if MOCK_AUDIT_LOGS else 1
    
    log_entry = {
        "id": new_id,
        "user_id": user_id,
        "action": action,
        "resource": resource,
        "details": details,
        "ip_address": ip_address,
        "user_agent": None,
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "status": status_code,
    }
    
    MOCK_AUDIT_LOGS.append(log_entry)
