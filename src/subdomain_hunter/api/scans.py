"""Scanning API endpoints."""
import json
import logging
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from sqlalchemy.orm import Session

from subdomain_hunter.db import get_db
from subdomain_hunter.auth_utils import get_current_user
from subdomain_hunter.models import (
    Domain,
    Subdomain,
    Vulnerability,
    ScanHistory,
    SubdomainResponse,
    VulnerabilityResponse,
    ScanHistoryResponse,
)
from subdomain_hunter.services import discovery_service, takeover_detector

logger = logging.getLogger(__name__)
router = APIRouter()


async def perform_scan(domain_id: int, db: Session):
    """Background task to perform a domain scan."""
    try:
        domain = db.query(Domain).filter(Domain.id == domain_id).first()
        if not domain:
            logger.error(f"Domain {domain_id} not found")
            return
        
        logger.info(f"Starting scan for domain {domain.domain_name}")
        
        # Create scan history entry
        scan = ScanHistory(domain_id=domain_id, status="running")
        db.add(scan)
        db.commit()
        
        start_time = datetime.utcnow()
        
        try:
            # Discover subdomains
            discovery_result = await discovery_service.discover_subdomains(domain.domain_name)
            
            # Process discovered subdomains
            existing_count = db.query(Subdomain).filter(Subdomain.domain_id == domain_id).count()
            new_subdomains = 0
            vulnerabilities_found = 0
            
            for subdomain, dns_records in discovery_result.get("subdomains", {}).items():
                # Check if subdomain already exists
                existing = db.query(Subdomain).filter(
                    Subdomain.domain_id == domain_id,
                    Subdomain.subdomain == subdomain,
                ).first()
                
                if not existing:
                    new_subdomains += 1
                    db_subdomain = Subdomain(
                        domain_id=domain_id,
                        subdomain=subdomain,
                        a_records=json.dumps(dns_records.get("A", [])),
                        aaaa_records=json.dumps(dns_records.get("AAAA", [])),
                        cname_record=dns_records.get("CNAME"),
                        mx_records=json.dumps(dns_records.get("MX", [])),
                        ns_records=json.dumps(dns_records.get("NS", [])),
                    )
                    db.add(db_subdomain)
                    db.flush()
                else:
                    db_subdomain = existing
                    # Update DNS records
                    db_subdomain.a_records = json.dumps(dns_records.get("A", []))
                    db_subdomain.aaaa_records = json.dumps(dns_records.get("AAAA", []))
                    db_subdomain.cname_record = dns_records.get("CNAME")
                    db_subdomain.mx_records = json.dumps(dns_records.get("MX", []))
                    db_subdomain.ns_records = json.dumps(dns_records.get("NS", []))
                    db.add(db_subdomain)
                    db.flush()
                
                # Check for takeover vulnerabilities
                vulnerabilities = await takeover_detector.check_takeover_risks(
                    subdomain, dns_records
                )
                
                for vuln in vulnerabilities:
                    existing_vuln = db.query(Vulnerability).filter(
                        Vulnerability.subdomain_id == db_subdomain.id,
                        Vulnerability.vuln_type == vuln["vuln_type"],
                    ).first()
                    
                    if not existing_vuln:
                        vulnerabilities_found += 1
                        db_vuln = Vulnerability(
                            subdomain_id=db_subdomain.id,
                            domain_id=domain_id,
                            vuln_type=vuln["vuln_type"],
                            confidence_score=vuln["confidence_score"],
                            details=vuln["details"],
                        )
                        db.add(db_vuln)
                    else:
                        # Update existing vulnerability
                        existing_vuln.confidence_score = vuln["confidence_score"]
                        existing_vuln.details = vuln["details"]
                        db.add(existing_vuln)
            
            db.commit()
            
            # Update scan history
            scan.status = "completed"
            scan.total_subdomains = len(discovery_result.get("subdomains", {}))
            scan.new_subdomains = new_subdomains
            scan.vulnerabilities_found = vulnerabilities_found
            scan.scan_duration_seconds = (datetime.utcnow() - start_time).total_seconds()
            db.add(scan)
            db.commit()
            
            # Update domain's last scanned time
            domain.last_scanned = datetime.utcnow()
            db.add(domain)
            db.commit()
            
            logger.info(
                f"Scan completed for {domain.domain_name}: "
                f"total={scan.total_subdomains}, new={new_subdomains}, vulns={vulnerabilities_found}"
            )
            
        except Exception as e:
            logger.error(f"Scan error for {domain.domain_name}: {e}")
            scan.status = "failed"
            scan.error_message = str(e)
            db.add(scan)
            db.commit()
    
    except Exception as e:
        logger.error(f"Unexpected error during scan: {e}")


@router.post("/{domain_id}/scan")
def trigger_scan(
    domain_id: int, 
    background_tasks: BackgroundTasks, 
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Trigger a scan for a domain."""
    domain = db.query(Domain).filter(Domain.id == domain_id).first()
    if not domain:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Domain with id {domain_id} not found",
        )
    
    # Add scan task to background
    background_tasks.add_task(perform_scan, domain_id, db)
    
    return {"message": f"Scan started for {domain.domain_name}", "domain_id": domain_id}


@router.get("/{domain_id}/results")
def get_scan_results(
    domain_id: int, 
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Get latest scan results for a domain."""
    domain = db.query(Domain).filter(Domain.id == domain_id).first()
    if not domain:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Domain with id {domain_id} not found",
        )
    
    subdomains = db.query(Subdomain).filter(Subdomain.domain_id == domain_id).all()
    vulnerabilities = db.query(Vulnerability).filter(Vulnerability.domain_id == domain_id).all()
    
    # Get last scan history
    last_scan = db.query(ScanHistory).filter(
        ScanHistory.domain_id == domain_id
    ).order_by(ScanHistory.scan_timestamp.desc()).first()
    
    return {
        "domain": domain,
        "subdomains": subdomains,
        "vulnerabilities": vulnerabilities,
        "last_scan": last_scan,
    }


@router.get("/history/{domain_id}")
def get_scan_history(
    domain_id: int, 
    skip: int = 0, 
    limit: int = 100, 
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Get scan history for a domain."""
    domain = db.query(Domain).filter(Domain.id == domain_id).first()
    if not domain:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Domain with id {domain_id} not found",
        )
    
    history = db.query(ScanHistory).filter(
        ScanHistory.domain_id == domain_id
    ).order_by(ScanHistory.scan_timestamp.desc()).offset(skip).limit(limit).all()
    
    return history
