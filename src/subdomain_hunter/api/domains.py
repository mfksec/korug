"""Domain management API endpoints."""
import logging
from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from subdomain_hunter.db import get_db
from subdomain_hunter.auth_utils import get_current_user
from subdomain_hunter.models import Domain, DomainCreate, DomainUpdate, DomainResponse

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("/", response_model=DomainResponse, status_code=status.HTTP_201_CREATED)
def create_domain(
    domain: DomainCreate, 
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Create a new domain to monitor."""
    # Check if domain already exists
    existing = db.query(Domain).filter(Domain.domain_name == domain.domain_name).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Domain {domain.domain_name} already exists",
        )
    
    db_domain = Domain(domain_name=domain.domain_name)
    db.add(db_domain)
    db.commit()
    db.refresh(db_domain)
    logger.info(f"Domain {domain.domain_name} created by {current_user['sub']}")
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
    
    db.delete(domain)
    db.commit()
    logger.info(f"Domain {domain_id} ({domain.domain_name}) deleted by {current_user['sub']}")
    return None
