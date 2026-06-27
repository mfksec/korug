"""Attack-surface change feed API.

Exposes the ``AssetChange`` log that scans write — the running record of how the
monitored surface moves over time (hosts appearing/disappearing, going
live/offline, IP/tech/port shifts, new certificates). Powers the Changes page
and the dashboard activity feed.
"""
import logging
from datetime import datetime, timedelta
from typing import List

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from korug.db import get_db
from korug.auth_utils import get_current_user
from korug.models import AssetChange, Domain

logger = logging.getLogger(__name__)
router = APIRouter()


def _serialize(ch: AssetChange, domain_name: str | None) -> dict:
    return {
        "id": ch.id,
        "domain_id": ch.domain_id,
        "domain_name": domain_name,
        "subdomain_id": ch.subdomain_id,
        "scan_id": ch.scan_id,
        "change_type": ch.change_type,
        "target": ch.target,
        "old_value": ch.old_value,
        "new_value": ch.new_value,
        "detected_at": ch.detected_at.isoformat() + "Z" if ch.detected_at else None,
    }


@router.get("/")
def list_changes(
    domain_id: int | None = Query(None, description="Filter to a single domain"),
    change_type: str | None = Query(None, description="Filter by change type"),
    since_days: int | None = Query(None, ge=1, le=365, description="Only changes in the last N days"),
    sort: str = Query("detected_at", description="Sort column: detected_at, change_type, target"),
    dir: str = Query("desc", description="Sort direction: asc or desc"),
    skip: int = 0,
    limit: int = Query(200, le=1000),
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """List attack-surface changes with filtering, sorting and pagination."""
    query = db.query(AssetChange, Domain.domain_name).join(
        Domain, AssetChange.domain_id == Domain.id
    )
    if domain_id is not None:
        query = query.filter(AssetChange.domain_id == domain_id)
    if change_type:
        query = query.filter(AssetChange.change_type == change_type)
    if since_days:
        query = query.filter(AssetChange.detected_at >= datetime.utcnow() - timedelta(days=since_days))

    total = query.count()

    sort_cols = {
        "detected_at": AssetChange.detected_at,
        "change_type": AssetChange.change_type,
        "target": AssetChange.target,
    }
    col = sort_cols.get(sort, AssetChange.detected_at)
    col = col.desc() if dir == "desc" else col.asc()
    rows = query.order_by(col).offset(skip).limit(limit).all()

    changes = [_serialize(ch, domain_name) for ch, domain_name in rows]
    return {"total": total, "count": len(changes), "changes": changes}


@router.get("/stats/summary")
def change_stats(
    since_days: int = Query(7, ge=1, le=365),
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """Counts per change type over the recent window (for the dashboard)."""
    from collections import defaultdict

    rows = db.query(AssetChange).filter(
        AssetChange.detected_at >= datetime.utcnow() - timedelta(days=since_days)
    ).all()
    by_type: dict = defaultdict(int)
    for ch in rows:
        by_type[ch.change_type] += 1
    return {"total": len(rows), "since_days": since_days, "by_type": dict(by_type)}
