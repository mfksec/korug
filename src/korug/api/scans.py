"""Scanning API endpoints."""
import json
import logging
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks, Query
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


# Scan lifecycle states. A scan moves running -> completed/failed, or a cancel
# request flips running -> cancelling, which the background task observes
# cooperatively and finalizes as cancelled.
ACTIVE_STATUSES = ("running", "cancelling")


class _ScanCancelled(Exception):
    """Raised internally when a cancel request is observed mid-scan."""


def _scan_cancel_requested(db: Session, scan_id: int) -> bool:
    """Return True if a cancel was requested for this scan.

    Issues a fresh SELECT so the long-running scan transaction observes the
    commit made by a separate cancel request (PostgreSQL READ COMMITTED).
    """
    current = db.query(ScanHistory.status).filter(ScanHistory.id == scan_id).scalar()
    return current in ("cancelling", "cancelled")


async def perform_scan(domain_id: int, db: Session, port_scan: bool | None = None):
    """Background task to perform a domain scan.

    ``port_scan`` overrides the configured default for this run (UI opt-in).
    """
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
            found = await discovery_service.discover(
                domain.domain_name,
                should_cancel=lambda: _scan_cancel_requested(db, scan.id),
            )
            names = list(found.keys())

            if _scan_cancel_requested(db, scan.id):
                raise _ScanCancelled()

            # 2. Enrich: DNS resolution, HTTP probe, Cloudflare, ports.
            #    Pass a cancel check so a long enrichment run stops promptly.
            enriched = await enrichment_service.enrich(
                names,
                port_scan=port_scan,
                should_cancel=lambda: _scan_cancel_requested(db, scan.id),
            )

            if _scan_cancel_requested(db, scan.id):
                raise _ScanCancelled()

            new_subdomains = 0
            vulnerabilities_found = 0
            persisted = 0

            for idx, subdomain in enumerate(names):
                # Cooperative cancellation: check periodically through the loop.
                if idx % 25 == 0 and _scan_cancel_requested(db, scan.id):
                    db.commit()  # keep whatever we've persisted so far
                    raise _ScanCancelled()

                res = enriched.get(subdomain)
                # Persist every discovered name, whether or not it currently
                # resolves, so the full passive footprint is visible. Resolution
                # state is captured via resolved_ips / is_alive.
                persisted += 1
                dns_records = res.dns_records if res else {}

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
                db_subdomain.resolved_ips = json.dumps(res.resolved_ips if res else [])
                db_subdomain.is_alive = res.is_alive if res else False
                db_subdomain.status_code = res.status_code if res else None
                db_subdomain.final_url = (res.final_url or None) and res.final_url[:512] if res else None
                db_subdomain.http_title = res.http_title if res else None
                db_subdomain.content_length = res.content_length if res else None
                db_subdomain.web_server = ((res.web_server or None) and res.web_server[:255]) if res else None
                db_subdomain.technologies = json.dumps(res.technologies if res else [])
                db_subdomain.open_ports = json.dumps(res.open_ports if res else [])
                db_subdomain.is_cloudflare = res.is_cloudflare if res else False
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

        except _ScanCancelled:
            db.rollback()
            logger.info(f"Scan cancelled for {domain.domain_name}")
            scan.status = "cancelled"
            scan.scan_duration_seconds = (datetime.utcnow() - start_time).total_seconds()
            db.add(scan)
            db.commit()
        except Exception as e:
            db.rollback()
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
    port_scan: bool | None = Query(None, description="Override the port-scan default for this run"),
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Trigger a scan for a domain. Set ?port_scan=true to include a port scan."""
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
        details={"domain_name": domain.domain_name, "port_scan": bool(port_scan)}
    )

    # Add scan task to background
    background_tasks.add_task(perform_scan, domain_id, db, port_scan)

    return {"message": f"Scan started for {domain.domain_name}", "domain_id": domain_id}


def _scan_status_payload(scan: ScanHistory | None) -> dict | None:
    if not scan:
        return None
    return {
        "id": scan.id,
        "domain_id": scan.domain_id,
        "status": scan.status,
        "is_active": scan.status in ACTIVE_STATUSES,
        "scan_timestamp": scan.scan_timestamp.isoformat() + "Z" if scan.scan_timestamp else None,
        "total_subdomains": scan.total_subdomains,
        "new_subdomains": scan.new_subdomains,
        "vulnerabilities_found": scan.vulnerabilities_found,
        "scan_duration_seconds": scan.scan_duration_seconds,
        "error_message": scan.error_message,
    }


@router.get("/active")
def get_active_scans(
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """List scans that are currently running or being cancelled.

    Used by the UI to show live scan state across the domains table without
    polling each domain individually.
    """
    scans = db.query(ScanHistory).filter(
        ScanHistory.status.in_(ACTIVE_STATUSES)
    ).all()
    return [_scan_status_payload(s) for s in scans]


@router.get("/{domain_id}/scan/status")
def get_scan_status(
    domain_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """Return the latest scan's status for a domain (for live polling)."""
    domain = db.query(Domain).filter(Domain.id == domain_id).first()
    if not domain:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Domain with id {domain_id} not found",
        )
    last_scan = db.query(ScanHistory).filter(
        ScanHistory.domain_id == domain_id
    ).order_by(ScanHistory.scan_timestamp.desc()).first()
    return {"domain_id": domain_id, "last_scan": _scan_status_payload(last_scan)}


@router.post("/{domain_id}/scan/cancel")
def cancel_scan(
    domain_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """Request cancellation of the in-progress scan for a domain.

    Cancellation is cooperative: the running background task observes the flag
    between discovery, enrichment, and persistence steps and stops at the next
    checkpoint, keeping any results already persisted.
    """
    domain = db.query(Domain).filter(Domain.id == domain_id).first()
    if not domain:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Domain with id {domain_id} not found",
        )

    running = db.query(ScanHistory).filter(
        ScanHistory.domain_id == domain_id,
        ScanHistory.status == "running",
    ).order_by(ScanHistory.scan_timestamp.desc()).first()

    if not running:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="No running scan to cancel for this domain",
        )

    running.status = "cancelling"
    db.add(running)
    db.commit()

    log_audit_event(
        AuditEvent.SCAN_TRIGGERED,
        user=current_user['sub'],
        resource_type="domain",
        resource_id=domain_id,
        details={"domain_name": domain.domain_name, "action": "cancel", "scan_id": running.id},
    )

    return {"message": f"Cancellation requested for {domain.domain_name}", "scan_id": running.id}


@router.get("/assets")
def list_assets(
    domain_id: int | None = Query(None, description="Filter to a single domain"),
    q: str | None = Query(None, description="Substring match on subdomain name"),
    alive: bool | None = Query(None, description="Filter by HTTP-alive state"),
    resolved: bool | None = Query(None, description="Filter by whether the name resolves"),
    skip: int = 0,
    limit: int = Query(500, le=2000),
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """List discovered assets (subdomains) across all domains.

    Powers the dedicated Assets page: a single searchable/filterable view of
    every subdomain found, joined to its parent domain name.
    """
    query = db.query(Subdomain, Domain.domain_name).join(
        Domain, Subdomain.domain_id == Domain.id
    )
    if domain_id is not None:
        query = query.filter(Subdomain.domain_id == domain_id)
    if q:
        query = query.filter(Subdomain.subdomain.ilike(f"%{q}%"))
    if alive is not None:
        query = query.filter(Subdomain.is_alive.is_(alive))

    total = query.count()
    rows = query.order_by(Subdomain.subdomain.asc()).offset(skip).limit(limit).all()

    assets = []
    for sub, domain_name in rows:
        item = _serialize_subdomain(sub)
        item["domain_id"] = sub.domain_id
        item["domain_name"] = domain_name
        item["resolves"] = bool(item["resolved_ips"])
        item["last_seen"] = sub.last_seen.isoformat() + "Z" if sub.last_seen else None
        assets.append(item)

    # `resolved` filters on derived state, so apply it after serialization.
    if resolved is not None:
        assets = [a for a in assets if a["resolves"] is resolved]

    return {"total": total, "count": len(assets), "assets": assets}


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
