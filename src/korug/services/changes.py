"""Attack-surface change detection.

Pure helpers that diff a subdomain's prior state against its freshly-enriched
state and emit change records, plus a persistence helper that writes
``AssetChange`` rows and raises ``Alert``s for the changes worth a human's
attention. This is the heart of Körüg's continuous-monitoring story: scans no
longer just snapshot the surface, they record how it moves.
"""
import json
import logging
from datetime import datetime
from typing import Dict, List, Optional

from sqlalchemy.orm import Session

from korug.models import Alert, AssetChange

logger = logging.getLogger(__name__)

# Change types that warrant a security alert, mapped to their severity. The
# rest (e.g. a benign tech string change) are logged to the change feed only.
_ALERTING = {
    "subdomain_added": "low",
    "went_live": "medium",
    "ports_changed": "medium",
    "new_certificate": "low",
    "subdomain_removed": "low",
}


def _norm_list(value) -> List[str]:
    return sorted(str(v) for v in (value or []))


def diff_subdomain(prior: Optional[Dict], current: Dict) -> List[Dict]:
    """Return the list of changes between a host's prior and current state.

    ``prior`` is ``None`` for a freshly-discovered host (the caller emits the
    ``subdomain_added`` event separately, since it owns the persistence
    timing). Each change is ``{change_type, old_value, new_value}``; the caller
    attaches domain/subdomain/scan context.
    """
    if prior is None:
        return []

    changes: List[Dict] = []

    was_alive = bool(prior.get("is_alive"))
    is_alive = bool(current.get("is_alive"))
    if was_alive != is_alive:
        changes.append({
            "change_type": "went_live" if is_alive else "went_offline",
            "old_value": str(prior.get("status_code") or "") or None,
            "new_value": str(current.get("status_code") or "") or None,
        })

    old_ips = _norm_list(prior.get("resolved_ips"))
    new_ips = _norm_list(current.get("resolved_ips"))
    if old_ips != new_ips:
        changes.append({
            "change_type": "ip_changed",
            "old_value": ", ".join(old_ips) or None,
            "new_value": ", ".join(new_ips) or None,
        })

    old_tech = _norm_list(prior.get("technologies"))
    new_tech = _norm_list(current.get("technologies"))
    if old_tech != new_tech:
        changes.append({
            "change_type": "tech_changed",
            "old_value": ", ".join(old_tech) or None,
            "new_value": ", ".join(new_tech) or None,
        })

    old_ports = _norm_list(p.get("port") if isinstance(p, dict) else p for p in (prior.get("open_ports") or []))
    new_ports = _norm_list(p.get("port") if isinstance(p, dict) else p for p in (current.get("open_ports") or []))
    if old_ports != new_ports:
        changes.append({
            "change_type": "ports_changed",
            "old_value": ", ".join(old_ports) or None,
            "new_value": ", ".join(new_ports) or None,
        })

    return changes


def _alert_message(change_type: str, target: str, new_value: Optional[str]) -> str:
    label = change_type.replace("_", " ")
    suffix = f" → {new_value}" if new_value else ""
    return f"{target}: {label}{suffix}"


def record_changes(
    db: Session,
    *,
    domain_id: int,
    subdomain_id: Optional[int],
    scan_id: Optional[int],
    target: str,
    changes: List[Dict],
    raise_alerts: bool = True,
) -> int:
    """Persist change records (and alerts for the significant ones).

    Adds rows to the current transaction; the caller commits. Returns the number
    of change rows recorded.
    """
    count = 0
    for change in changes:
        ctype = change.get("change_type")
        if not ctype:
            continue
        db.add(AssetChange(
            domain_id=domain_id,
            subdomain_id=subdomain_id,
            scan_id=scan_id,
            change_type=ctype,
            target=target,
            old_value=change.get("old_value"),
            new_value=change.get("new_value"),
        ))
        count += 1

        severity = _ALERTING.get(ctype)
        if raise_alerts and severity:
            db.add(Alert(
                domain_id=domain_id,
                target=target,
                alert_type=f"change:{ctype}",
                severity=severity,
                message=_alert_message(ctype, target, change.get("new_value")),
            ))
    return count
