"""Certificate Transparency lookup against crt.sh.

Given a hostname this queries crt.sh's JSON endpoint and returns the observed
TLS certificates (issuer, common name, SANs, serial, validity window). Used to
surface a host's certificate history in the detail view and to monitor for
newly-issued certificates (a strong attack-surface signal).

Best-effort like the rest of recon: failures are logged and yield an empty list
so a slow/unavailable crt.sh never fails a scan. Responses are cached in-process
to avoid hammering the endpoint when several hosts are scanned in quick
succession. Mirrors the patterns in ``services/cve.py`` and ``services/discovery.py``.
"""
import logging
import time
from datetime import datetime
from typing import Dict, List, Optional, Tuple

import aiohttp

logger = logging.getLogger(__name__)

CRTSH_URL = "https://crt.sh/"
_CACHE_TTL = 1800  # seconds
_cache: Dict[str, Tuple[float, list]] = {}

# crt.sh emits timestamps like "2024-01-02T03:04:05".
_TS_FORMATS = ("%Y-%m-%dT%H:%M:%S", "%Y-%m-%d %H:%M:%S")


def _parse_ts(value: Optional[str]) -> Optional[datetime]:
    if not value:
        return None
    for fmt in _TS_FORMATS:
        try:
            return datetime.strptime(value, fmt)
        except (ValueError, TypeError):
            continue
    return None


def _parse_row(row: dict) -> Optional[dict]:
    """Normalize one crt.sh JSON row into our certificate shape."""
    serial = (row.get("serial_number") or "").strip() or None
    common_name = (row.get("common_name") or "").strip() or None
    # name_value is a newline-separated list of SANs.
    sans = sorted({
        n.strip().lower()
        for n in (row.get("name_value") or "").split("\n")
        if n.strip()
    })
    return {
        "serial_number": serial,
        "issuer": (row.get("issuer_name") or "").strip() or None,
        "common_name": common_name,
        "sans": sans,
        "not_before": _parse_ts(row.get("not_before")),
        "not_after": _parse_ts(row.get("not_after")),
        "source": "crt.sh",
    }


async def fetch_certificates(host: str, timeout_s: int = 20) -> List[dict]:
    """Return de-duplicated certificates observed for ``host`` via crt.sh.

    De-dup is by serial number (falling back to a CN+validity key when a serial
    is absent). The most recently-issued certificate for each serial wins.
    """
    host = (host or "").strip().lower().rstrip(".")
    if not host:
        return []

    cached = _cache.get(host)
    if cached and (time.time() - cached[0]) < _CACHE_TTL:
        return cached[1]

    params = {"q": host, "output": "json"}
    timeout = aiohttp.ClientTimeout(total=timeout_s)
    rows: list = []
    try:
        async with aiohttp.ClientSession(timeout=timeout,
                                         headers={"User-Agent": "korug-recon/1.0"}) as session:
            async with session.get(CRTSH_URL, params=params) as resp:
                if resp.status != 200:
                    logger.warning("crt.sh returned %s for %r", resp.status, host)
                    _cache[host] = (time.time(), [])
                    return []
                rows = await resp.json(content_type=None)
    except Exception as e:
        logger.warning("crt.sh query failed for %r: %s", host, e)
        return []

    by_key: Dict[str, dict] = {}
    for row in rows or []:
        cert = _parse_row(row)
        if not cert:
            continue
        key = cert["serial_number"] or f"{cert['common_name']}|{cert['not_after']}"
        existing = by_key.get(key)
        # Keep the entry with the latest not_before for a given key.
        if not existing or (cert["not_before"] and existing.get("not_before") and
                            cert["not_before"] > existing["not_before"]):
            by_key[key] = cert

    out = sorted(
        by_key.values(),
        key=lambda c: c["not_before"] or datetime.min,
        reverse=True,
    )
    _cache[host] = (time.time(), out)
    return out
