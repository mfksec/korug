"""Audit logging utilities for security events."""
import json
import logging
from datetime import datetime
from enum import Enum
from typing import Any, Optional

logger = logging.getLogger("audit")


class AuditEvent(str, Enum):
    """Security audit event types."""
    # Authentication events
    LOGIN_SUCCESS = "login_success"
    LOGIN_FAILED = "login_failed"
    LOGOUT = "logout"
    TOKEN_REFRESH = "token_refresh"
    TOKEN_REFRESH_FAILED = "token_refresh_failed"
    
    # API key events
    API_KEY_CREATED = "api_key_created"
    API_KEY_REVOKED = "api_key_revoked"
    API_KEY_DELETED = "api_key_deleted"

    # User management events
    USER_CREATED = "user_created"
    USER_UPDATED = "user_updated"
    USER_DELETED = "user_deleted"
    PASSWORD_CHANGED = "password_changed"
    PASSWORD_RESET = "password_reset"

    # Integration events
    INTEGRATION_UPDATED = "integration_updated"
    INTEGRATION_TESTED = "integration_tested"
    
    # Data events
    DOMAIN_CREATED = "domain_created"
    DOMAIN_DELETED = "domain_deleted"
    DOMAIN_UPDATED = "domain_updated"
    SCAN_TRIGGERED = "scan_triggered"
    EXPORT_INITIATED = "export_initiated"
    VULNERABILITY_UPDATED = "vulnerability_updated"
    VULNERABILITY_DELETED = "vulnerability_deleted"
    
    # Access events
    UNAUTHORIZED_ACCESS_ATTEMPT = "unauthorized_access_attempt"
    FORBIDDEN_OPERATION = "forbidden_operation"
    

def log_audit_event(
    event: AuditEvent,
    user: Optional[str] = None,
    resource_type: Optional[str] = None,
    resource_id: Optional[Any] = None,
    details: Optional[dict] = None,
    status: str = "success",
) -> None:
    """Log a security audit event.
    
    Args:
        event: The type of audit event
        user: Username/email of the user performing the action
        resource_type: Type of resource affected (domain, scan, etc.)
        resource_id: ID of the resource
        details: Additional details about the event
        status: Whether the action was 'success' or 'failure'
    """
    audit_entry = {
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "event": event.value,
        "user": user or "anonymous",
        "resource_type": resource_type,
        "resource_id": resource_id,
        "status": status,
        "details": details or {},
    }

    # Log as JSON for structured logging
    logger.info(json.dumps(audit_entry))

    # Persist to the database so the dashboard can surface real audit history.
    _persist_audit_event(
        event=event.value,
        user=user or "anonymous",
        resource_type=resource_type,
        resource_id=resource_id,
        status=status,
        details=details or {},
    )


def _persist_audit_event(
    event: str,
    user: str,
    resource_type: Optional[str],
    resource_id: Optional[Any],
    status: str,
    details: dict,
) -> None:
    """Best-effort persistence of an audit event to the database.

    Uses its own short-lived session so it can be called from any context
    (auth flows, background tasks, request handlers) without threading a
    session through every call site. Failures are swallowed so audit logging
    never breaks the primary operation.
    """
    try:
        # Imported lazily to avoid import-time coupling with the DB layer.
        from korug.db import SessionLocal
        from korug.models import AuditLog

        db = SessionLocal()
        try:
            entry = AuditLog(
                user=user,
                event=event,
                resource_type=resource_type,
                resource_id=str(resource_id) if resource_id is not None else None,
                status=status,
                details=json.dumps(details) if details else None,
            )
            db.add(entry)
            db.commit()
        finally:
            db.close()
    except Exception as exc:  # pragma: no cover - defensive
        logger.debug(f"Could not persist audit event to DB: {exc}")


def setup_audit_logger(log_file: str = "audit.log") -> None:
    """Configure audit logger with file handler.
    
    Args:
        log_file: Path to audit log file
    """
    from logging.handlers import RotatingFileHandler
    
    # Create logger if it doesn't exist
    if not logger.handlers:
        # Rotating file handler - max 10MB per file, keep 10 backups
        handler = RotatingFileHandler(
            log_file,
            maxBytes=10_000_000,  # 10 MB
            backupCount=10,
        )
        
        # Structured JSON format
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)
        logger.setLevel(logging.INFO)
