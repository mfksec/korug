"""Vulnerability management API endpoints."""
import logging
from typing import List
from datetime import datetime, timedelta
from collections import defaultdict

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session

from korug.db import get_db
from korug.auth_utils import get_current_user
from korug.audit import log_audit_event, AuditEvent
from korug.models import Vulnerability, VulnerabilityUpdate, VulnerabilityResponse

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/", response_model=List[VulnerabilityResponse])
def list_vulnerabilities(
    domain_id: int | None = Query(None),
    vuln_type: str | None = Query(None),
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """List vulnerabilities with optional filtering."""
    query = db.query(Vulnerability)
    
    if domain_id:
        query = query.filter(Vulnerability.domain_id == domain_id)
    
    if vuln_type:
        query = query.filter(Vulnerability.vuln_type == vuln_type)
    
    vulnerabilities = query.offset(skip).limit(limit).all()
    return vulnerabilities


@router.get("/{vuln_id}", response_model=VulnerabilityResponse)
def get_vulnerability(
    vuln_id: int, 
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """Get a specific vulnerability."""
    vuln = db.query(Vulnerability).filter(Vulnerability.id == vuln_id).first()
    if not vuln:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Vulnerability with id {vuln_id} not found",
        )
    return vuln


@router.patch("/{vuln_id}", response_model=VulnerabilityResponse)
def update_vulnerability(
    vuln_id: int,
    update: VulnerabilityUpdate,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """Update vulnerability (mark as false positive, etc.)."""
    vuln = db.query(Vulnerability).filter(Vulnerability.id == vuln_id).first()
    if not vuln:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Vulnerability with id {vuln_id} not found",
        )
    
    vuln.is_false_positive = update.is_false_positive
    vuln.false_positive_reason = update.false_positive_reason
    
    db.add(vuln)
    db.commit()
    db.refresh(vuln)
    
    log_audit_event(
        AuditEvent.VULNERABILITY_UPDATED,
        user=current_user['sub'],
        resource_type="vulnerability",
        resource_id=vuln_id,
        details={
            "is_false_positive": update.is_false_positive,
            "reason": update.false_positive_reason
        }
    )
    
    return vuln


@router.delete("/{vuln_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_vulnerability(
    vuln_id: int, 
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """Delete a vulnerability record."""
    vuln = db.query(Vulnerability).filter(Vulnerability.id == vuln_id).first()
    if not vuln:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Vulnerability with id {vuln_id} not found",
        )
    
    log_audit_event(
        AuditEvent.VULNERABILITY_DELETED,
        user=current_user['sub'],
        resource_type="vulnerability",
        resource_id=vuln_id,
        details={"vulnerability_type": getattr(vuln, 'vulnerability_type', 'unknown')}
    )
    
    db.delete(vuln)
    db.commit()
    return None


# Chart/Analytics Endpoints

@router.get("/stats/summary")
def get_vulnerability_stats(
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """Get vulnerability statistics for charts.
    
    Returns: {
        total: int,
        critical: int,
        high: int,
        medium: int,
        low: int,
        avg_confidence: float,
        by_type: {type: count}
    }
    """
    all_vulns = db.query(Vulnerability).all()
    total = len(all_vulns)

    avg_confidence = (
        sum(v.confidence_score for v in all_vulns) / total if total else 0.0
    )

    type_counts = defaultdict(int)
    for v in all_vulns:
        if v.vuln_type:
            type_counts[v.vuln_type] += 1

    return {
        "total": total,
        "critical": len([v for v in all_vulns if v.confidence_score >= 90]),
        "high": len([v for v in all_vulns if 70 <= v.confidence_score < 90]),
        "medium": len([v for v in all_vulns if 50 <= v.confidence_score < 70]),
        "low": len([v for v in all_vulns if v.confidence_score < 50]),
        "avg_confidence": round(avg_confidence, 1),
        "by_type": dict(type_counts),
    }


@router.get("/stats/timeline")
def get_vulnerability_timeline(
    days: int = Query(30, ge=1, le=365), 
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """Get vulnerability discovery timeline for the past N days.
    
    Returns: [{date: "YYYY-MM-DD", count: int}, ...]
    """
    now = datetime.utcnow()

    # Count real vulnerabilities discovered per day within the window.
    date_counts = defaultdict(int)
    vulns = db.query(Vulnerability).filter(
        Vulnerability.found_at >= now - timedelta(days=days)
    ).all()
    for v in vulns:
        if v.found_at:
            date_counts[v.found_at.date().isoformat()] += 1

    # Emit one entry per day so the chart has a continuous x-axis (zeros included).
    timeline = []
    for i in range(days):
        date = (now - timedelta(days=days - i - 1)).date().isoformat()
        timeline.append({"date": date, "count": date_counts.get(date, 0)})

    return timeline


@router.get("/stats/confidence-distribution")
def get_confidence_distribution(
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """Get vulnerability distribution by confidence score severity.
    
    Returns: [
        {severity: "critical", count: int, percentage: float},
        ...
    ]
    """
    all_vulns = db.query(Vulnerability).all()

    critical = len([v for v in all_vulns if v.confidence_score >= 90])
    high = len([v for v in all_vulns if 70 <= v.confidence_score < 90])
    medium = len([v for v in all_vulns if 50 <= v.confidence_score < 70])
    low = len([v for v in all_vulns if v.confidence_score < 50])

    total = len(all_vulns)
    
    return [
        {"severity": "critical", "score_range": "90-100", "count": critical, "percentage": round(critical/total*100) if total else 0},
        {"severity": "high", "score_range": "70-89", "count": high, "percentage": round(high/total*100) if total else 0},
        {"severity": "medium", "score_range": "50-69", "count": medium, "percentage": round(medium/total*100) if total else 0},
        {"severity": "low", "score_range": "0-49", "count": low, "percentage": round(low/total*100) if total else 0},
    ]
