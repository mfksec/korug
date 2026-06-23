"""Scanning API endpoints."""
import json
import logging
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from sqlalchemy.orm import Session

from korug.db import get_db
from korug.auth_utils import get_current_user
from korug.audit import log_audit_event, AuditEvent
from korug.models import (
    Domain,
    Subdomain,
    Vulnerability,
    ScanHistory,
    Alert,
    SubdomainResponse,
    VulnerabilityResponse,
    ScanHistoryResponse,
)
from korug.services import discovery_service, enrichment_service, takeover_detector

logger = logging.getLogger(__name__)
router = APIRouter()


def _severity_from_confidence(score: float) -> str:
    """Map a vulnerability confidence score (0-100) to an alert severity."""
    if score >= 90:
        return "critical"
    if score >= 70:
        return "high"
    if score >= 50:
        return "medium"
    return "low"


def _alert_message(subdomain: str, vuln_type: str, details: str | None) -> str:
    """Build a human-readable alert message from a vulnerability finding."""
    summary = vuln_type.replace("_", " ")
    if details:
        try:
            parsed = json.loads(details)
            if isinstance(parsed, dict) and parsed.get("message"):
                summary = parsed["message"]
        except (ValueError, TypeError):
            pass
    return f"{subdomain}: {summary}"


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
            # 1. Passive discovery across many sources
            found = await discovery_service.discover(domain.domain_name)
            names = list(found.keys())

            # 2. Enrich: DNS resolution, HTTP probe, Cloudflare, ports
            enriched = await enrichment_service.enrich(names)

            new_subdomains = 0
            vulnerabilities_found = 0
            persisted = 0

            for subdomain in names:
                res = enriched.get(subdomain)
                # Only persist subdomains that actually resolve to something.
                if not res or not res.resolved():
                    continue
                persisted += 1
                dns_records = res.dns_records

                existing = db.query(Subdomain).filter(
                    Subdomain.domain_id == domain_id,
                    Subdomain.subdomain == subdomain,
                ).first()

                if not existing:
                    new_subdomains += 1
                    db_subdomain = Subdomain(domain_id=domain_id, subdomain=subdomain)
                else:
                    db_subdomain = existing

                # DNS records
                db_subdomain.a_records = json.dumps(dns_records.get("A", []))
                db_subdomain.aaaa_records = json.dumps(dns_records.get("AAAA", []))
                db_subdomain.cname_record = dns_records.get("CNAME")
                db_subdomain.mx_records = json.dumps(dns_records.get("MX", []))
                db_subdomain.ns_records = json.dumps(dns_records.get("NS", []))
                # Provenance + enrichment
                db_subdomain.sources = ",".join(sorted(found.get(subdomain, [])))
                db_subdomain.resolved_ips = json.dumps(res.resolved_ips)
                db_subdomain.is_alive = res.is_alive
                db_subdomain.status_code = res.status_code
                db_subdomain.final_url = (res.final_url or None) and res.final_url[:512]
                db_subdomain.http_title = res.http_title
                db_subdomain.content_length = res.content_length
                db_subdomain.web_server = (res.web_server or None) and res.web_server[:255]
                db_subdomain.technologies = json.dumps(res.technologies)
                db_subdomain.open_ports = json.dumps(res.open_ports)
                db_subdomain.is_cloudflare = res.is_cloudflare
                db_subdomain.last_enriched = datetime.utcnow()
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
                        db.flush()

                        # Raise a security alert for the newly found vulnerability
                        db.add(Alert(
                            domain_id=domain_id,
                            vulnerability_id=db_vuln.id,
                            target=subdomain,
                            alert_type=vuln["vuln_type"],
                            severity=_severity_from_confidence(vuln["confidence_score"]),
                            message=_alert_message(subdomain, vuln["vuln_type"], vuln["details"]),
                        ))
                    else:
                        # Update existing vulnerability
                        existing_vuln.confidence_score = vuln["confidence_score"]
                        existing_vuln.details = vuln["details"]
                        db.add(existing_vuln)
            
            db.commit()
            
            # Update scan history
            scan.status = "completed"
            scan.total_subdomains = persisted
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
    
    log_audit_event(
        AuditEvent.SCAN_TRIGGERED,
        user=current_user['sub'],
        resource_type="domain",
        resource_id=domain_id,
        details={"domain_name": domain.domain_name}
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

    last_scan = db.query(ScanHistory).filter(
        ScanHistory.domain_id == domain_id
    ).order_by(ScanHistory.scan_timestamp.desc()).first()

    sub_dicts = [_serialize_subdomain(s) for s in subdomains]

    # Classify: group subdomains that resolve to the same IP address.
    ip_map: dict[str, list[str]] = {}
    for s in sub_dicts:
        for ip in s["resolved_ips"]:
            ip_map.setdefault(ip, []).append(s["subdomain"])
    ip_groups = [
        {"ip": ip, "subdomains": sorted(names), "count": len(names)}
        for ip, names in sorted(ip_map.items(), key=lambda kv: len(kv[1]), reverse=True)
    ]

    return {
        "domain": {
            "id": domain.id,
            "domain_name": domain.domain_name,
            "enabled": domain.enabled,
            "last_scanned": domain.last_scanned.isoformat() + "Z" if domain.last_scanned else None,
        },
        "counts": {
            "subdomains": len(sub_dicts),
            "alive": len([s for s in sub_dicts if s["is_alive"]]),
            "vulnerabilities": len(vulnerabilities),
            "cloudflare": len([s for s in sub_dicts if s["is_cloudflare"]]),
        },
        "ip_groups": ip_groups,
        "subdomains": sub_dicts,
        "vulnerabilities": [_serialize_vuln(v) for v in vulnerabilities],
        "last_scan": {
            "status": last_scan.status,
            "scan_timestamp": last_scan.scan_timestamp.isoformat() + "Z" if last_scan.scan_timestamp else None,
            "total_subdomains": last_scan.total_subdomains,
            "new_subdomains": last_scan.new_subdomains,
            "vulnerabilities_found": last_scan.vulnerabilities_found,
            "scan_duration_seconds": last_scan.scan_duration_seconds,
        } if last_scan else None,
    }


def _json_list(value: str | None) -> list:
    try:
        return json.loads(value) if value else []
    except (ValueError, TypeError):
        return []


def _serialize_subdomain(s: Subdomain) -> dict:
    return {
        "id": s.id,
        "subdomain": s.subdomain,
        "sources": (s.sources or "").split(",") if s.sources else [],
        "resolved_ips": _json_list(s.resolved_ips) or _json_list(s.a_records),
        "cname": s.cname_record,
        "is_alive": bool(s.is_alive),
        "status_code": s.status_code,
        "final_url": s.final_url,
        "http_title": s.http_title,
        "content_length": s.content_length,
        "web_server": s.web_server,
        "technologies": _json_list(s.technologies),
        "open_ports": _json_list(s.open_ports),
        "is_cloudflare": bool(s.is_cloudflare),
        "first_discovered": s.first_discovered.isoformat() + "Z" if s.first_discovered else None,
    }


def _serialize_vuln(v: Vulnerability) -> dict:
    return {
        "id": v.id,
        "subdomain_id": v.subdomain_id,
        "vuln_type": v.vuln_type,
        "confidence_score": v.confidence_score,
        "details": v.details,
        "is_false_positive": v.is_false_positive,
        "found_at": v.found_at.isoformat() + "Z" if v.found_at else None,
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
