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
    Certificate,
    AssetChange,
    ScanHistory,
    Alert,
    SubdomainResponse,
    VulnerabilityResponse,
    ScanHistoryResponse,
)
from korug.services import discovery_service, enrichment_service, takeover_detector
from korug.services import cve as cve_service
from korug.services import certificates as cert_service
from korug.services import changes as change_service
from korug.services import nuclei as nuclei_service

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


def _host_state(res) -> dict:
    """Snapshot the comparable fields of an enrichment result for change diffing."""
    return {
        "is_alive": bool(res.is_alive) if res else False,
        "status_code": res.status_code if res else None,
        "resolved_ips": list(res.resolved_ips) if res else [],
        "technologies": list(res.technologies) if res else [],
        "open_ports": list(res.open_ports) if res else [],
    }


def _subdomain_state(sub: Subdomain) -> dict:
    """Snapshot the comparable fields of a persisted subdomain (its prior state)."""
    return {
        "is_alive": bool(sub.is_alive),
        "status_code": sub.status_code,
        "resolved_ips": _json_list(sub.resolved_ips) or _json_list(sub.a_records),
        "technologies": _json_list(sub.technologies),
        "open_ports": _json_list(sub.open_ports),
    }


async def _scan_cves(db: Session, sub: Subdomain, res, nvd_key: str | None) -> int:
    """Look up CVEs for a host's fingerprinted software and upsert findings.

    Shared by the manual per-subdomain scan and the incremental auto-scan.
    Returns the count of newly-created findings.
    """
    if not res:
        return 0
    try:
        cves = await cve_service.lookup(res.web_server, res.technologies, api_key=nvd_key)
    except Exception as e:
        logger.warning("CVE lookup failed for %s: %s", sub.subdomain, e)
        return 0

    new_vulns = 0
    for c in cves:
        vuln_type = f"cve:{c['cve_id']}"
        existing = db.query(Vulnerability).filter(
            Vulnerability.subdomain_id == sub.id,
            Vulnerability.vuln_type == vuln_type,
        ).first()
        score = float(c["cvss"]) * 10 if c.get("cvss") else 50.0
        details = json.dumps({
            "category": "cve",
            "cve_id": c["cve_id"],
            "cvss": c.get("cvss"),
            "severity": c.get("severity"),
            "product": c.get("product"),
            "version": c.get("version"),
            "summary": c.get("summary"),
            "match": "keyword",
            "message": f"{c.get('product')} {c.get('version')}: {c['cve_id']} ({c.get('severity')})",
        })
        if existing:
            existing.confidence_score = score
            existing.details = details
            db.add(existing)
            continue
        new_vulns += 1
        db_vuln = Vulnerability(
            subdomain_id=sub.id, domain_id=sub.domain_id,
            vuln_type=vuln_type, confidence_score=score, details=details,
        )
        db.add(db_vuln)
        db.flush()
        # Alert on the serious ones only.
        if (c.get("severity") or "").upper() in ("HIGH", "CRITICAL"):
            db.add(Alert(
                domain_id=sub.domain_id, vulnerability_id=db_vuln.id, target=sub.subdomain,
                alert_type="cve", severity=(c["severity"] or "high").lower(),
                message=f"{sub.subdomain}: {c['cve_id']} in {c.get('product')} {c.get('version')}",
            ))
    return new_vulns


async def _scan_certificates(db: Session, sub: Subdomain, scan_id: int | None = None) -> int:
    """Fetch crt.sh certificates for a host and upsert them.

    The first observation of a host establishes a silent baseline; on later
    scans a previously-unseen serial is recorded as a ``new_certificate`` change
    (and alerted). Returns the count of newly-stored certificates.
    """
    had_baseline = db.query(Certificate).filter(Certificate.subdomain_id == sub.id).count() > 0
    try:
        certs = await cert_service.fetch_certificates(sub.subdomain)
    except Exception as e:
        logger.warning("Certificate fetch failed for %s: %s", sub.subdomain, e)
        return 0

    new_certs = 0
    for c in certs:
        serial = c.get("serial_number")
        existing = None
        if serial:
            existing = db.query(Certificate).filter(
                Certificate.subdomain_id == sub.id,
                Certificate.serial_number == serial,
            ).first()
        if existing:
            existing.last_seen = datetime.utcnow()
            existing.issuer = c.get("issuer")
            existing.common_name = c.get("common_name")
            existing.sans = json.dumps(c.get("sans") or [])
            existing.not_before = c.get("not_before")
            existing.not_after = c.get("not_after")
            db.add(existing)
            continue
        new_certs += 1
        db.add(Certificate(
            subdomain_id=sub.id, domain_id=sub.domain_id,
            issuer=c.get("issuer"), common_name=c.get("common_name"),
            sans=json.dumps(c.get("sans") or []),
            serial_number=serial,
            not_before=c.get("not_before"), not_after=c.get("not_after"),
            source=c.get("source") or "crt.sh",
        ))
        # Only flag genuinely-new issuances once a baseline exists, so the first
        # scan doesn't alert on every historical certificate.
        if had_baseline:
            change_service.record_changes(
                db, domain_id=sub.domain_id, subdomain_id=sub.id, scan_id=scan_id,
                target=sub.subdomain,
                changes=[{
                    "change_type": "new_certificate",
                    "old_value": None,
                    "new_value": f"{c.get('common_name') or '?'} ({c.get('issuer') or 'unknown issuer'})",
                }],
            )
    return new_certs


async def _run_incremental_enrichment(db: Session, scan, incremental_ids: list[int], enriched: dict) -> int:
    """Run CVE lookup + certificate monitoring for new/changed alive hosts.

    Best-effort and fully fault-isolated: each host is processed and committed on
    its own, so a network error, timeout, or rate-limit on one host (or the whole
    NVD/crt.sh service) is logged and skipped without failing the scan or losing
    the other hosts' results. Returns the count of newly-created CVE findings.

    Raises only ``_ScanCancelled`` (when a cancel is requested between hosts).
    """
    from korug.config import get_settings
    cfg = get_settings()
    if not incremental_ids or not (cfg.enable_auto_cve or cfg.enable_cert_monitoring):
        return 0

    nvd_key = None
    try:
        from korug.api.integrations import get_recon_keys
        nvd_key = get_recon_keys(db).get("nvd") or cfg.nvd_api_key or None
    except Exception as e:
        logger.warning("Could not load recon keys (continuing without): %s", e)

    logger.info("Incremental enrichment: %d host(s) for CVE/cert lookup", len(incremental_ids))
    new_vulns = 0
    for sub_id in incremental_ids:
        if _scan_cancel_requested(db, scan.id):
            raise _ScanCancelled()
        try:
            sub = db.query(Subdomain).filter(Subdomain.id == sub_id).first()
            if not sub:
                continue
            res = enriched.get(sub.subdomain)
            if cfg.enable_auto_cve:
                n = await _scan_cves(db, sub, res, nvd_key)
                db.commit()       # persist this host's findings before moving on
                new_vulns += n
            if cfg.enable_cert_monitoring:
                await _scan_certificates(db, sub, scan_id=scan.id)
                db.commit()
        except _ScanCancelled:
            raise
        except Exception as e:
            # Contain any failure (HTTP error, rate-limit, DB issue) to this host.
            logger.warning("Incremental enrichment failed for subdomain id=%s (skipping): %s", sub_id, e)
            try:
                db.rollback()
            except Exception:
                pass
    return new_vulns


async def _run_nuclei(db: Session, scan, incremental_ids: list[int], enriched: dict) -> int:
    """Active template scanning (nuclei) over the incremental alive host set.

    Opt-in (``enable_nuclei``) and caller-gated to active monitor mode. nuclei is
    run once over the whole batch (it parallelizes internally). Fully fault-isolated:
    a missing binary, timeout, or any error is logged and yields no findings.
    Returns the count of newly-created findings.
    """
    cfg = get_settings()
    if not cfg.enable_nuclei or not incremental_ids:
        return 0

    # Build hostname → subdomain and the target URL list (alive hosts only).
    host_to_id: dict[str, int] = {}
    urls: list[str] = []
    for sub_id in incremental_ids:
        sub = db.query(Subdomain).filter(Subdomain.id == sub_id).first()
        if not sub:
            continue
        res = enriched.get(sub.subdomain)
        if not (res and res.is_alive):
            continue
        host_to_id[sub.subdomain.lower()] = sub.id
        urls.append((res.final_url or f"https://{sub.subdomain}"))

    if not urls:
        return 0

    try:
        findings = await nuclei_service.scan(urls)
    except Exception as e:
        logger.warning("nuclei scan failed (continuing): %s", e)
        return 0

    new_vulns = 0
    try:
        for f in findings:
            sub_id = host_to_id.get((f.get("host") or "").lower())
            if not sub_id:
                continue
            sub = db.query(Subdomain).filter(Subdomain.id == sub_id).first()
            if not sub:
                continue
            vuln_type = f"nuclei:{f['template_id']}"[:100]
            existing = db.query(Vulnerability).filter(
                Vulnerability.subdomain_id == sub.id,
                Vulnerability.vuln_type == vuln_type,
            ).first()
            score = nuclei_service.severity_confidence(f.get("severity"))
            details = json.dumps({
                "category": "nuclei",
                "template_id": f["template_id"],
                "name": f.get("name"),
                "severity": f.get("severity"),
                "matched_at": f.get("matched_at"),
                "description": f.get("description"),
                "message": f"{f.get('name')} ({f.get('severity')}) — {f.get('matched_at') or sub.subdomain}",
            })
            if existing:
                existing.confidence_score = score
                existing.details = details
                db.add(existing)
                continue
            new_vulns += 1
            db_vuln = Vulnerability(
                subdomain_id=sub.id, domain_id=sub.domain_id,
                vuln_type=vuln_type, confidence_score=score, details=details,
            )
            db.add(db_vuln)
            db.flush()
            if (f.get("severity") or "").lower() in ("high", "critical"):
                db.add(Alert(
                    domain_id=sub.domain_id, vulnerability_id=db_vuln.id, target=sub.subdomain,
                    alert_type="nuclei", severity=f["severity"].lower(),
                    message=f"{sub.subdomain}: {f.get('name')} ({f.get('severity')})",
                ))
        db.commit()
    except Exception as e:
        logger.warning("Persisting nuclei findings failed (continuing): %s", e)
        db.rollback()
        return 0
    return new_vulns


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
        
        # Passive monitoring stays low-touch: discovery + DNS + DNS-based takeover
        # only, no HTTP probing (and therefore no tech/CVE/cert/port enrichment).
        passive = (domain.monitor_mode or "active") == "passive"
        logger.info(f"Starting {'passive' if passive else 'active'} scan for domain {domain.domain_name}")

        # Create scan history entry
        scan = ScanHistory(domain_id=domain_id, status="running")
        db.add(scan)
        db.commit()
        
        start_time = datetime.utcnow()

        try:
            # 1. Passive discovery across many sources (UI-configured API keys
            #    override the env defaults).
            from korug.api.integrations import get_recon_keys
            recon_keys = get_recon_keys(db)
            found = await discovery_service.discover(
                domain.domain_name,
                should_cancel=lambda: _scan_cancel_requested(db, scan.id),
                keys=recon_keys,
            )
            names = list(found.keys())

            if _scan_cancel_requested(db, scan.id):
                raise _ScanCancelled()

            # 2. Enrich: DNS resolution, HTTP probe, Cloudflare, ports.
            #    Pass a cancel check so a long enrichment run stops promptly.
            #    Passive mode skips HTTP probing and port scanning entirely.
            enriched = await enrichment_service.enrich(
                names,
                port_scan=False if passive else port_scan,
                http_probe=False if passive else None,
                should_cancel=lambda: _scan_cancel_requested(db, scan.id),
            )

            if _scan_cancel_requested(db, scan.id):
                raise _ScanCancelled()

            new_subdomains = 0
            vulnerabilities_found = 0
            persisted = 0
            # subdomain ids worth a CVE/cert pass this scan (new or changed-alive)
            incremental_ids: list[int] = []

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

                # Capture prior state for change detection before we overwrite it.
                prior_state = _subdomain_state(existing) if existing else None
                was_gone = bool(existing.is_gone) if existing else False

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
                # Touch last_seen explicitly so "seen this scan" is unambiguous
                # even when no other column changed (drives gone-detection below).
                db_subdomain.last_seen = datetime.utcnow()
                # A name seen again is no longer gone.
                db_subdomain.is_gone = False
                db_subdomain.gone_at = None
                db.add(db_subdomain)
                db.flush()

                # Record attack-surface changes for this host.
                current_state = _host_state(res)
                diffs = change_service.diff_subdomain(prior_state, current_state)
                if prior_state is None:
                    diffs = [{"change_type": "subdomain_added", "old_value": None,
                              "new_value": ", ".join(current_state["resolved_ips"]) or None}]
                elif was_gone:
                    diffs = [{"change_type": "subdomain_readded", "old_value": None,
                              "new_value": ", ".join(current_state["resolved_ips"]) or None}] + diffs
                if diffs:
                    change_service.record_changes(
                        db, domain_id=domain_id, subdomain_id=db_subdomain.id,
                        scan_id=scan.id, target=subdomain, changes=diffs,
                    )

                # A host is "incremental" (worth a CVE/cert pass) if it's new, was
                # gone, or its alive/tech state changed — keeps NVD volume bounded.
                tech_or_alive_changed = any(
                    d["change_type"] in ("went_live", "tech_changed") for d in diffs
                )
                if current_state["is_alive"] and (prior_state is None or was_gone or tech_or_alive_changed):
                    incremental_ids.append(db_subdomain.id)

                # Check for takeover vulnerabilities (pass the probed body so the
                # precise service-fingerprint check can run).
                vulnerabilities = await takeover_detector.check_takeover_risks(
                    subdomain, dns_records,
                    http_body=(res.http_body if res else None),
                    status_code=(res.status_code if res else None),
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

            # Incremental enrichment: CVE lookup + certificate monitoring for the
            # bounded set of new/changed alive hosts. This phase is best-effort and
            # network-bound (NVD + crt.sh, both rate-limited): every host is
            # isolated and committed independently so a single error, timeout, or
            # rate-limit can never break the scan or lose other hosts' results.
            vulnerabilities_found += await _run_incremental_enrichment(
                db, scan, incremental_ids, enriched
            )

            # Active template scanning (nuclei) — active monitor mode only, opt-in.
            if not passive:
                vulnerabilities_found += await _run_nuclei(db, scan, incremental_ids, enriched)

            # Gone-tracking: names present in a prior scan but absent from this
            # one (last_seen older than this scan) are flagged gone + logged once.
            # Best-effort: a failure here must not fail an otherwise-good scan.
            try:
                gone_subs = db.query(Subdomain).filter(
                    Subdomain.domain_id == domain_id,
                    Subdomain.is_gone.is_(False),
                    Subdomain.last_seen < start_time,
                ).all()
                for gone in gone_subs:
                    gone.is_gone = True
                    gone.gone_at = datetime.utcnow()
                    db.add(gone)
                    change_service.record_changes(
                        db, domain_id=domain_id, subdomain_id=gone.id, scan_id=scan.id,
                        target=gone.subdomain,
                        changes=[{"change_type": "subdomain_removed",
                                  "old_value": ", ".join(_json_list(gone.resolved_ips)) or None,
                                  "new_value": None}],
                    )
                if gone_subs:
                    db.commit()
            except _ScanCancelled:
                raise
            except Exception as e:
                logger.warning("Gone-tracking failed for %s (continuing): %s", domain.domain_name, e)
                db.rollback()

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
    gone: bool | None = Query(None, description="Filter by gone (disappeared) state"),
    sort: str = Query("subdomain", description="Sort column: subdomain, last_seen, first_discovered, status_code"),
    dir: str = Query("asc", description="Sort direction: asc or desc"),
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
    if gone is not None:
        query = query.filter(Subdomain.is_gone.is_(gone))

    total = query.count()

    sort_cols = {
        "subdomain": Subdomain.subdomain,
        "last_seen": Subdomain.last_seen,
        "first_discovered": Subdomain.first_discovered,
        "status_code": Subdomain.status_code,
    }
    col = sort_cols.get(sort, Subdomain.subdomain)
    col = col.desc() if dir == "desc" else col.asc()
    rows = query.order_by(col).offset(skip).limit(limit).all()

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


@router.post("/subdomain/{subdomain_id}/scan")
async def scan_subdomain(
    subdomain_id: int,
    port_scan: bool | None = Query(None, description="Include a port scan for this host"),
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """Re-scan a single subdomain: refresh DNS/HTTP/tech/ports + takeover check.

    Runs inline (one host is quick) and returns the refreshed asset. CVE lookup
    is layered on here in a later phase.
    """
    sub = db.query(Subdomain).filter(Subdomain.id == subdomain_id).first()
    if not sub:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Subdomain not found")

    log_audit_event(
        AuditEvent.SCAN_TRIGGERED,
        user=current_user['sub'],
        resource_type="subdomain",
        resource_id=subdomain_id,
        details={"subdomain": sub.subdomain, "port_scan": bool(port_scan)},
    )

    enriched = await enrichment_service.enrich([sub.subdomain], port_scan=port_scan)
    res = enriched.get(sub.subdomain)
    dns_records = res.dns_records if res else {}

    sub.a_records = json.dumps(dns_records.get("A", []))
    sub.aaaa_records = json.dumps(dns_records.get("AAAA", []))
    sub.cname_record = dns_records.get("CNAME")
    sub.mx_records = json.dumps(dns_records.get("MX", []))
    sub.ns_records = json.dumps(dns_records.get("NS", []))
    sub.resolved_ips = json.dumps(res.resolved_ips if res else [])
    sub.is_alive = res.is_alive if res else False
    sub.status_code = res.status_code if res else None
    sub.final_url = ((res.final_url or None) and res.final_url[:512]) if res else None
    sub.http_title = res.http_title if res else None
    sub.content_length = res.content_length if res else None
    sub.web_server = ((res.web_server or None) and res.web_server[:255]) if res else None
    sub.technologies = json.dumps(res.technologies if res else [])
    sub.open_ports = json.dumps(res.open_ports if res else [])
    sub.is_cloudflare = res.is_cloudflare if res else False
    sub.last_enriched = datetime.utcnow()
    db.add(sub)
    db.flush()

    # Takeover detection for this host (precise service-fingerprint check uses the body)
    vulns = await takeover_detector.check_takeover_risks(
        sub.subdomain, dns_records,
        http_body=(res.http_body if res else None),
        status_code=(res.status_code if res else None),
    )
    new_vulns = 0
    for vuln in vulns:
        existing = db.query(Vulnerability).filter(
            Vulnerability.subdomain_id == sub.id,
            Vulnerability.vuln_type == vuln["vuln_type"],
        ).first()
        if existing:
            existing.confidence_score = vuln["confidence_score"]
            existing.details = vuln["details"]
            db.add(existing)
            continue
        new_vulns += 1
        db_vuln = Vulnerability(
            subdomain_id=sub.id, domain_id=sub.domain_id,
            vuln_type=vuln["vuln_type"], confidence_score=vuln["confidence_score"],
            details=vuln["details"],
        )
        db.add(db_vuln)
        db.flush()
        db.add(Alert(
            domain_id=sub.domain_id, vulnerability_id=db_vuln.id, target=sub.subdomain,
            alert_type=vuln["vuln_type"], severity=_severity_from_confidence(vuln["confidence_score"]),
            message=_alert_message(sub.subdomain, vuln["vuln_type"], vuln["details"]),
        ))

    # Persist the enrichment + takeover findings before the network-bound CVE/cert
    # work, so a rate-limit or error in that step can never discard them.
    db.commit()

    # CVE lookup + certificate monitoring (best-effort) for this host. Both reuse
    # the shared helpers so the manual and incremental auto-scan stay in lockstep,
    # and both are fully contained: a failure here is logged, not surfaced as a 500.
    from korug.config import get_settings
    cfg = get_settings()
    try:
        if cfg.enable_cve_scan and res:
            from korug.api.integrations import get_recon_keys
            nvd_key = get_recon_keys(db).get("nvd") or cfg.nvd_api_key or None
            new_vulns += await _scan_cves(db, sub, res, nvd_key)
        if cfg.enable_cert_monitoring:
            await _scan_certificates(db, sub)
        db.commit()
    except Exception as e:
        logger.warning("CVE/cert enrichment failed for %s (returning enrichment only): %s", sub.subdomain, e)
        db.rollback()

    db.refresh(sub)
    asset = _serialize_subdomain(sub)
    asset["domain_id"] = sub.domain_id
    asset["resolves"] = bool(asset["resolved_ips"])
    return {"asset": asset, "new_vulnerabilities": new_vulns}


@router.get("/subdomain/{subdomain_id}")
def get_subdomain_detail(
    subdomain_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """Full detail for one subdomain: asset + vulnerabilities + certificates + changes.

    Powers the per-host detail view.
    """
    sub = db.query(Subdomain).filter(Subdomain.id == subdomain_id).first()
    if not sub:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Subdomain not found")

    domain = db.query(Domain).filter(Domain.id == sub.domain_id).first()
    vulns = db.query(Vulnerability).filter(Vulnerability.subdomain_id == sub.id).all()
    certs = db.query(Certificate).filter(
        Certificate.subdomain_id == sub.id
    ).order_by(Certificate.not_before.desc().nullslast()).all()
    changes = db.query(AssetChange).filter(
        AssetChange.subdomain_id == sub.id
    ).order_by(AssetChange.detected_at.desc()).limit(50).all()

    asset = _serialize_subdomain(sub)
    asset["domain_id"] = sub.domain_id
    asset["domain_name"] = domain.domain_name if domain else None
    asset["resolves"] = bool(asset["resolved_ips"])
    asset["last_seen"] = sub.last_seen.isoformat() + "Z" if sub.last_seen else None
    asset["gone_at"] = sub.gone_at.isoformat() + "Z" if sub.gone_at else None

    return {
        "asset": asset,
        "vulnerabilities": [_serialize_vuln(v) for v in vulns],
        "certificates": [_serialize_cert(c) for c in certs],
        "changes": [_serialize_change(ch) for ch in changes],
    }


@router.post("/subdomain/{subdomain_id}/certificates/refresh")
async def refresh_subdomain_certificates(
    subdomain_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """Re-fetch certificates from crt.sh for one host and upsert them.

    Returns the refreshed certificate list and how many were newly stored.
    """
    sub = db.query(Subdomain).filter(Subdomain.id == subdomain_id).first()
    if not sub:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Subdomain not found")

    new_certs = await _scan_certificates(db, sub)
    db.commit()

    certs = db.query(Certificate).filter(
        Certificate.subdomain_id == sub.id
    ).order_by(Certificate.not_before.desc().nullslast()).all()
    return {"new_certificates": new_certs, "certificates": [_serialize_cert(c) for c in certs]}


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
            "monitor_mode": domain.monitor_mode,
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
        "dns_records": {
            "A": _json_list(s.a_records),
            "AAAA": _json_list(s.aaaa_records),
            "CNAME": s.cname_record,
            "MX": _json_list(s.mx_records),
            "NS": _json_list(s.ns_records),
        },
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
        "is_gone": bool(s.is_gone),
        "first_discovered": s.first_discovered.isoformat() + "Z" if s.first_discovered else None,
    }


def _serialize_cert(c: Certificate) -> dict:
    return {
        "id": c.id,
        "subdomain_id": c.subdomain_id,
        "domain_id": c.domain_id,
        "issuer": c.issuer,
        "common_name": c.common_name,
        "sans": _json_list(c.sans),
        "serial_number": c.serial_number,
        "not_before": c.not_before.isoformat() + "Z" if c.not_before else None,
        "not_after": c.not_after.isoformat() + "Z" if c.not_after else None,
        "source": c.source,
        "first_seen": c.first_seen.isoformat() + "Z" if c.first_seen else None,
        "last_seen": c.last_seen.isoformat() + "Z" if c.last_seen else None,
    }


def _serialize_change(ch: AssetChange) -> dict:
    return {
        "id": ch.id,
        "domain_id": ch.domain_id,
        "subdomain_id": ch.subdomain_id,
        "scan_id": ch.scan_id,
        "change_type": ch.change_type,
        "target": ch.target,
        "old_value": ch.old_value,
        "new_value": ch.new_value,
        "detected_at": ch.detected_at.isoformat() + "Z" if ch.detected_at else None,
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
