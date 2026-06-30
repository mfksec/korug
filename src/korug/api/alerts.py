"""Alert management API endpoints."""
import logging
from typing import List
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from korug.db import get_db
from korug.auth_utils import get_current_user, require_role
from korug.audit import log_audit_event, AuditEvent
from korug.models import Alert, Domain

logger = logging.getLogger(__name__)
router = APIRouter()


class AlertResponse(BaseModel):
    id: int
    domain: str
    alert_type: str
    severity: str
    message: str
    created_at: str
    resolved_at: str | None = None
    is_resolved: bool = False

    class Config:
        from_attributes = True


def _serialize(alert: Alert) -> dict:
    """Convert an Alert ORM row into the API response shape."""
    return {
        "id": alert.id,
        "domain": alert.target,
        "alert_type": alert.alert_type,
        "severity": alert.severity,
        "message": alert.message,
        "created_at": alert.created_at.isoformat() + "Z" if alert.created_at else "",
        "resolved_at": alert.resolved_at.isoformat() + "Z" if alert.resolved_at else None,
        "is_resolved": alert.is_resolved,
    }


@router.get("/", response_model=List[AlertResponse])
def list_alerts(
    status: str = Query("all", pattern="^(all|active|resolved)$"),
    severity: str | None = Query(None, pattern="^(critical|high|medium|low)$"),
    domain: str | None = Query(None),
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """List security alerts generated from real scan findings.

    Query parameters:
    - status: 'all', 'active', or 'resolved'
    - severity: filter by severity level
    - domain: filter by affected domain/subdomain name
    - skip / limit: pagination
    """
    query = db.query(Alert)

    if status == "active":
        query = query.filter(Alert.is_resolved.is_(False))
    elif status == "resolved":
        query = query.filter(Alert.is_resolved.is_(True))

    if severity:
        query = query.filter(Alert.severity == severity)

    if domain:
        query = query.filter(Alert.target.ilike(f"%{domain}%"))

    alerts = (
        query.order_by(Alert.created_at.desc())
        .offset(skip)
        .limit(limit)
        .all()
    )
    return [_serialize(a) for a in alerts]


@router.get("/{alert_id}", response_model=AlertResponse)
def get_alert(
    alert_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """Get a specific alert."""
    alert = db.query(Alert).filter(Alert.id == alert_id).first()
    if not alert:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Alert with id {alert_id} not found",
        )
    return _serialize(alert)


@router.post("/{alert_id}/resolve", response_model=AlertResponse)
def resolve_alert(
    alert_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_role("admin")),
):
    """Mark an alert as resolved."""
    alert = db.query(Alert).filter(Alert.id == alert_id).first()
    if not alert:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Alert with id {alert_id} not found",
        )

    alert.is_resolved = True
    alert.resolved_at = datetime.utcnow()
    db.add(alert)
    db.commit()
    db.refresh(alert)
    return _serialize(alert)


@router.post("/{alert_id}/unresolve", response_model=AlertResponse)
def unresolve_alert(
    alert_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_role("admin")),
):
    """Mark a resolved alert as unresolved."""
    alert = db.query(Alert).filter(Alert.id == alert_id).first()
    if not alert:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Alert with id {alert_id} not found",
        )

    alert.is_resolved = False
    alert.resolved_at = None
    db.add(alert)
    db.commit()
    db.refresh(alert)
    return _serialize(alert)


@router.get("/stats/summary")
def get_alert_stats(
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """Get alert statistics.

    Returns: {
        total: int,
        active: int,
        resolved: int,
        by_severity: {critical: int, high: int, medium: int, low: int}
    }
    """
    alerts = db.query(Alert).all()

    return {
        "total": len(alerts),
        "active": len([a for a in alerts if not a.is_resolved]),
        "resolved": len([a for a in alerts if a.is_resolved]),
        "by_severity": {
            "critical": len([a for a in alerts if a.severity == "critical"]),
            "high": len([a for a in alerts if a.severity == "high"]),
            "medium": len([a for a in alerts if a.severity == "medium"]),
            "low": len([a for a in alerts if a.severity == "low"]),
        },
    }


@router.delete("/{alert_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_alert(
    alert_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_role("admin")),
):
    """Delete an alert."""
    alert = db.query(Alert).filter(Alert.id == alert_id).first()
    if not alert:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Alert with id {alert_id} not found",
        )

    db.delete(alert)
    db.commit()
    return None
