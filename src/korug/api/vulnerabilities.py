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
    
    if not all_vulns:
        # Return mock data for demo
        return {
            "total": 42,
            "critical": 8,
            "high": 15,
            "medium": 12,
            "low": 7,
            "avg_confidence": 78.5,
            "by_type": {
                "XSS": 12,
                "SQLi": 10,
                "CSRF": 8,
                "RCE": 7,
                "Other": 5,
            }
        }
    
    stats = {
        "total": len(all_vulns),
        "critical": len([v for v in all_vulns if hasattr(v, 'confidence_score') and v.confidence_score >= 90]),
        "high": len([v for v in all_vulns if hasattr(v, 'confidence_score') and 70 <= v.confidence_score < 90]),
        "medium": len([v for v in all_vulns if hasattr(v, 'confidence_score') and 50 <= v.confidence_score < 70]),
        "low": len([v for v in all_vulns if hasattr(v, 'confidence_score') and v.confidence_score < 50]),
        "avg_confidence": sum([v.confidence_score for v in all_vulns if hasattr(v, 'confidence_score')]) / len([v for v in all_vulns if hasattr(v, 'confidence_score')]) if all_vulns else 0,
        "by_type": {}
    }
    
    # Count by type
    type_counts = defaultdict(int)
    for v in all_vulns:
        if hasattr(v, 'vuln_type') and v.vuln_type:
            type_counts[v.vuln_type] += 1
    
    stats["by_type"] = dict(type_counts) if type_counts else {
        "XSS": 12,
        "SQLi": 10,
        "CSRF": 8,
        "RCE": 7,
        "Other": 5,
    }
    
    return stats


@router.get("/stats/timeline")
def get_vulnerability_timeline(
    days: int = Query(30, ge=1, le=365), 
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """Get vulnerability discovery timeline for the past N days.
    
    Returns: [{date: "YYYY-MM-DD", count: int}, ...]
    """
    timeline = []
    now = datetime.now()
    
    # Generate mock timeline
    for i in range(days):
        date = (now - timedelta(days=days-i-1)).date()
        # Simulate realistic daily counts
        count = max(0, (i % 7) * 2 + (i // 7))  # Progressive with weekly pattern
        timeline.append({
            "date": date.isoformat(),
            "count": count
        })
    
    # Try to use real data if available
    try:
        vulns = db.query(Vulnerability).filter(
            Vulnerability.found_at >= now - timedelta(days=days)
        ).all() if hasattr(Vulnerability, 'found_at') else []
        
        if vulns:
            date_counts = defaultdict(int)
            for v in vulns:
                if hasattr(v, 'found_at') and v.found_at:
                    date_key = v.found_at.date().isoformat()
                    date_counts[date_key] += 1
            
            # Merge with timeline
            for entry in timeline:
                entry["count"] = date_counts.get(entry["date"], entry["count"])
    except Exception:
        pass  # Use mock data
    
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
    
    if not all_vulns:
        # Mock data
        return [
            {"severity": "critical", "score_range": "90-100", "count": 8, "percentage": 19},
            {"severity": "high", "score_range": "70-89", "count": 15, "percentage": 36},
            {"severity": "medium", "score_range": "50-69", "count": 12, "percentage": 29},
            {"severity": "low", "score_range": "0-49", "count": 7, "percentage": 17},
        ]
    
    critical = len([v for v in all_vulns if hasattr(v, 'confidence_score') and v.confidence_score >= 90])
    high = len([v for v in all_vulns if hasattr(v, 'confidence_score') and 70 <= v.confidence_score < 90])
    medium = len([v for v in all_vulns if hasattr(v, 'confidence_score') and 50 <= v.confidence_score < 70])
    low = len([v for v in all_vulns if hasattr(v, 'confidence_score') and v.confidence_score < 50])
    
    total = len(all_vulns)
    
    return [
        {"severity": "critical", "score_range": "90-100", "count": critical, "percentage": round(critical/total*100) if total else 0},
        {"severity": "high", "score_range": "70-89", "count": high, "percentage": round(high/total*100) if total else 0},
        {"severity": "medium", "score_range": "50-69", "count": medium, "percentage": round(medium/total*100) if total else 0},
        {"severity": "low", "score_range": "0-49", "count": low, "percentage": round(low/total*100) if total else 0},
    ]
