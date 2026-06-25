"""Domain management API endpoints."""
import logging
from typing import List

from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from sqlalchemy.orm import Session

from korug.db import get_db
from korug.auth_utils import get_current_user
from korug.audit import log_audit_event, AuditEvent
from korug.models import (
    Domain,
    Vulnerability,
    ScanHistory,
    DomainCreate,
    DomainUpdate,
    DomainResponse,
)

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/stats/dashboard")
def get_dashboard_stats(
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """Aggregate stats for the dashboard home, computed from real data."""
    total_domains = db.query(Domain).count()

    total_vulnerabilities = db.query(Vulnerability).filter(
        Vulnerability.is_false_positive.is_(False)
    ).count()

    active_scans = db.query(ScanHistory).filter(
        ScanHistory.status == "running"
    ).count()

    # A domain is "high risk" if it has at least one high-confidence vulnerability.
    high_risk_domains = (
        db.query(Vulnerability.domain_id)
        .filter(
            Vulnerability.confidence_score >= 70,
            Vulnerability.is_false_positive.is_(False),
        )
        .distinct()
        .count()
    )

    return {
        "total_domains": total_domains,
        "total_vulnerabilities": total_vulnerabilities,
        "active_scans": active_scans,
        "high_risk_domains": high_risk_domains,
    }


@router.post("/", response_model=DomainResponse, status_code=status.HTTP_201_CREATED)
def create_domain(
    domain: DomainCreate,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Create a new domain to monitor. Discovery starts automatically."""
    # Check if domain already exists
    existing = db.query(Domain).filter(Domain.domain_name == domain.domain_name).first()
    if existing:
        log_audit_event(
            AuditEvent.DOMAIN_CREATED,
            user=current_user['sub'],
            resource_type="domain",
            resource_id=existing.id,
            status="failure",
            details={"reason": "already_exists"}
        )
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Domain {domain.domain_name} already exists",
        )
    
    db_domain = Domain(domain_name=domain.domain_name)
    db.add(db_domain)
    db.commit()
    db.refresh(db_domain)
    
    log_audit_event(
        AuditEvent.DOMAIN_CREATED,
        user=current_user['sub'],
        resource_type="domain",
        resource_id=db_domain.id,
        details={"domain_name": domain.domain_name}
    )
    logger.info(f"Domain {domain.domain_name} created by {current_user['sub']}")

    # Continuous monitoring: kick off subdomain discovery immediately so the
    # operator sees assets without a manual scan step.
    from korug.api.scans import perform_scan
    background_tasks.add_task(perform_scan, db_domain.id, db, False)

    return db_domain


@router.get("/", response_model=List[DomainResponse])
def list_domains(
    skip: int = 0, 
    limit: int = 100, 
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """List all monitored domains."""
    domains = db.query(Domain).offset(skip).limit(limit).all()
    return domains


@router.get("/{domain_id}", response_model=DomainResponse)
def get_domain(
    domain_id: int, 
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Get a specific domain."""
    domain = db.query(Domain).filter(Domain.id == domain_id).first()
    if not domain:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Domain with id {domain_id} not found",
        )
    return domain


@router.put("/{domain_id}", response_model=DomainResponse)
def update_domain(
    domain_id: int, 
    domain: DomainUpdate, 
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Update a domain."""
    db_domain = db.query(Domain).filter(Domain.id == domain_id).first()
    if not db_domain:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Domain with id {domain_id} not found",
        )
    
    update_data = domain.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(db_domain, field, value)
    
    db.add(db_domain)
    db.commit()
    db.refresh(db_domain)
    logger.info(f"Domain {domain_id} updated by {current_user['sub']}")
    return db_domain


@router.delete("/{domain_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_domain(
    domain_id: int, 
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Delete a domain."""
    domain = db.query(Domain).filter(Domain.id == domain_id).first()
    if not domain:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Domain with id {domain_id} not found",
        )
    
    log_audit_event(
        AuditEvent.DOMAIN_DELETED,
        user=current_user['sub'],
        resource_type="domain",
        resource_id=domain_id,
        details={"domain_name": domain.domain_name}
    )
    
    db.delete(domain)
    db.commit()
    logger.info(f"Domain {domain_id} ({domain.domain_name}) deleted by {current_user['sub']}")
    return None
