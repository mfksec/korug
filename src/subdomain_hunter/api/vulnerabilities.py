"""Vulnerability management API endpoints."""
import logging
from typing import List

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session

from subdomain_hunter.db import get_db
from subdomain_hunter.models import Vulnerability, VulnerabilityUpdate, VulnerabilityResponse

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/", response_model=List[VulnerabilityResponse])
def list_vulnerabilities(
    domain_id: int | None = Query(None),
    vuln_type: str | None = Query(None),
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
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
def get_vulnerability(vuln_id: int, db: Session = Depends(get_db)):
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
    return vuln


@router.delete("/{vuln_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_vulnerability(vuln_id: int, db: Session = Depends(get_db)):
    """Delete a vulnerability record."""
    vuln = db.query(Vulnerability).filter(Vulnerability.id == vuln_id).first()
    if not vuln:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Vulnerability with id {vuln_id} not found",
        )
    
    db.delete(vuln)
    db.commit()
    return None
