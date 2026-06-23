"""Alert management API endpoints."""
import logging
from typing import List
from datetime import datetime
from enum import Enum

from fastapi import APIRouter, Depends, HTTPException, status, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from korug.db import get_db
from korug.auth_utils import get_current_user
from korug.audit import log_audit_event, AuditEvent

logger = logging.getLogger(__name__)
router = APIRouter()


# Enums for alert types and severity
class AlertType(str, Enum):
    TAKEOVER_DETECTED = "takeover_detected"
    XSS_FOUND = "xss_found"
    SQLI_FOUND = "sqli_found"
    SSL_WEAK = "ssl_weak"
    MISCONFIG = "misconfig"
    OTHER = "other"


class AlertSeverity(str, Enum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class AlertResponse(BaseModel):
    id: int
    domain: str
    alert_type: AlertType
    severity: AlertSeverity
    message: str
    created_at: str
    resolved_at: str | None = None
    is_resolved: bool = False

    class Config:
        from_attributes = True


class AlertCreate(BaseModel):
    domain: str
    alert_type: AlertType
    severity: AlertSeverity
    message: str


# Mock data for alerts
MOCK_ALERTS = [
    {
        "id": 1,
        "domain": "example.com",
        "alert_type": "takeover_detected",
        "severity": "critical",
        "message": "Subdomain takeover detected on subdomain.example.com - DNS points to unclaimed service",
        "created_at": "2026-06-20T10:30:00Z",
        "resolved_at": None,
        "is_resolved": False,
    },
    {
        "id": 2,
        "domain": "api.example.com",
        "alert_type": "xss_found",
        "severity": "high",
        "message": "Reflected XSS vulnerability found in search parameter",
        "created_at": "2026-06-19T14:20:00Z",
        "resolved_at": None,
        "is_resolved": False,
    },
    {
        "id": 3,
        "domain": "admin.example.com",
        "alert_type": "sqli_found",
        "severity": "critical",
        "message": "SQL Injection vulnerability in login form detected",
        "created_at": "2026-06-18T09:15:00Z",
        "resolved_at": "2026-06-19T16:45:00Z",
        "is_resolved": True,
    },
    {
        "id": 4,
        "domain": "mail.example.com",
        "alert_type": "ssl_weak",
        "severity": "medium",
        "message": "SSL/TLS certificate uses weak cipher suite",
        "created_at": "2026-06-17T11:00:00Z",
        "resolved_at": None,
        "is_resolved": False,
    },
]


@router.get("/", response_model=List[AlertResponse])
def list_alerts(
    status: str = Query("all", pattern="^(all|active|resolved)$"),
    severity: AlertSeverity | None = Query(None),
    domain: str | None = Query(None),
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """List alerts with optional filtering.
    
    Query parameters:
    - status: 'all', 'active', or 'resolved'
    - severity: filter by severity level
    - domain: filter by domain name
    - skip: pagination offset
    - limit: pagination limit
    """
    # Using mock data for now (no database model yet)
    alerts = MOCK_ALERTS.copy()
    
    # Filter by status
    if status == "active":
        alerts = [a for a in alerts if not a["is_resolved"]]
    elif status == "resolved":
        alerts = [a for a in alerts if a["is_resolved"]]
    
    # Filter by severity
    if severity:
        alerts = [a for a in alerts if a["severity"] == severity]
    
    # Filter by domain
    if domain:
        alerts = [a for a in alerts if domain.lower() in a["domain"].lower()]
    
    # Apply pagination
    total = len(alerts)
    alerts = alerts[skip : skip + limit]
    
    return alerts


@router.get("/{alert_id}", response_model=AlertResponse)
def get_alert(
    alert_id: int, 
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Get a specific alert."""
    for alert in MOCK_ALERTS:
        if alert["id"] == alert_id:
            return alert
    
    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail=f"Alert with id {alert_id} not found",
    )


@router.post("/", response_model=AlertResponse)
def create_alert(
    alert: AlertCreate,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """Create a new alert."""
    new_id = max([a["id"] for a in MOCK_ALERTS]) + 1 if MOCK_ALERTS else 1
    new_alert = {
        "id": new_id,
        "domain": alert.domain,
        "alert_type": alert.alert_type,
        "severity": alert.severity,
        "message": alert.message,
        "created_at": datetime.utcnow().isoformat() + "Z",
        "resolved_at": None,
        "is_resolved": False,
    }
    MOCK_ALERTS.append(new_alert)
    return new_alert


@router.post("/{alert_id}/resolve", response_model=AlertResponse)
def resolve_alert(
    alert_id: int, 
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Mark an alert as resolved."""
    for alert in MOCK_ALERTS:
        if alert["id"] == alert_id:
            alert["is_resolved"] = True
            alert["resolved_at"] = datetime.utcnow().isoformat() + "Z"
            return alert
    
    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail=f"Alert with id {alert_id} not found",
    )


@router.post("/{alert_id}/unresolve", response_model=AlertResponse)
def unresolve_alert(
    alert_id: int, 
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Mark a resolved alert as unresolved."""
    for alert in MOCK_ALERTS:
        if alert["id"] == alert_id:
            alert["is_resolved"] = False
            alert["resolved_at"] = None
            return alert
    
    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail=f"Alert with id {alert_id} not found",
    )


@router.get("/stats/summary")
def get_alert_stats(
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Get alert statistics.
    
    Returns: {
        total: int,
        active: int,
        resolved: int,
        by_severity: {critical: int, high: int, medium: int, low: int}
    }
    """
    alerts = MOCK_ALERTS
    
    return {
        "total": len(alerts),
        "active": len([a for a in alerts if not a["is_resolved"]]),
        "resolved": len([a for a in alerts if a["is_resolved"]]),
        "by_severity": {
            "critical": len([a for a in alerts if a["severity"] == "critical"]),
            "high": len([a for a in alerts if a["severity"] == "high"]),
            "medium": len([a for a in alerts if a["severity"] == "medium"]),
            "low": len([a for a in alerts if a["severity"] == "low"]),
        }
    }


@router.delete("/{alert_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_alert(
    alert_id: int, 
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Delete an alert."""
    for i, alert in enumerate(MOCK_ALERTS):
        if alert["id"] == alert_id:
            MOCK_ALERTS.pop(i)
            return None
    
    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail=f"Alert with id {alert_id} not found",
    )
