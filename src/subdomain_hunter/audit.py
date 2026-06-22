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
