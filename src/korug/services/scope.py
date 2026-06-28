"""Ownership attribution and scope gating for active scanning.

"Scope is law": before Körüg points an active, intrusive tool (nuclei, port scan)
at an asset, it must be confident the asset is one the operator is authorized to
probe. This module derives an **ownership confidence** score and the per-tool
authorization decisions from deterministic, offline signals:

- **Name ownership** — the host is a subdomain of a monitored domain (you added it).
- **IP ownership** — a resolved IP falls inside a declared owned range (``SCOPE_CIDRS``).
- **Third-party app hosting** — the CNAME points at a known third-party application
  service (e.g. ``*.github.io``, ``*.herokuapp.com``); the *app* is someone else's
  even though the *name* is yours, so host-level active scanning would hit them.

Two gates fall out of this:

- ``host_active_allowed`` (nuclei / HTTP-level): owned by name and not third-party-app
  hosted. CDN-fronting is fine — it's still your application.
- ``port_scan_allowed`` (IP-level): the IP is yours and not a shared CDN address.
"""
from typing import Dict, List, Optional

from korug.services.enrichment import is_cloudflare_ip, ip_in_cidrs
from korug.services.takeover_fingerprints import match_cname


def _name_in_scope(name: str, apexes: List[str]) -> bool:
    n = (name or "").lower().rstrip(".")
    return any(n == a or n.endswith("." + a) for a in apexes)


def classify(
    subdomain: str,
    resolved_ips: Optional[List[str]],
    cname: Optional[str],
    *,
    owned_cidrs: Optional[List[str]] = None,
    monitored_apexes: Optional[List[str]] = None,
) -> Dict:
    """Return ownership signals, a 0-100 confidence score, and per-tool gates."""
    resolved_ips = resolved_ips or []
    owned_cidrs = owned_cidrs or []
    apexes = [a.lower().rstrip(".") for a in (monitored_apexes or [])]
    cname_n = (cname or "").lower().rstrip(".")

    name_owned = _name_in_scope(subdomain, apexes)
    ip_owned = any(ip_in_cidrs(ip, owned_cidrs) for ip in resolved_ips)
    on_cdn = any(is_cloudflare_ip(ip) for ip in resolved_ips)
    # CNAME to a known third-party application host (takeover-fingerprint services
    # are a good proxy) that isn't one of our own domains and isn't a CDN.
    third_party_app = bool(cname_n) and not _name_in_scope(cname_n, apexes) \
        and bool(match_cname(cname_n)) and not on_cdn

    if ip_owned:
        hosting = "first_party"
    elif on_cdn:
        hosting = "cdn"
    elif third_party_app:
        hosting = "third_party"
    elif cname_n and not _name_in_scope(cname_n, apexes):
        hosting = "external"
    else:
        hosting = "unknown"

    score = 0
    if name_owned:
        score += 50
    if ip_owned:
        score += 40
    if not third_party_app:
        score += 10
    score = max(0, min(100, score))

    return {
        "confidence": float(score),
        "hosting": hosting,
        "name_owned": name_owned,
        "ip_owned": ip_owned,
        "on_cdn": on_cdn,
        "third_party_app": third_party_app,
        # Host-level active scanning (nuclei): yours by name and not someone else's app.
        "host_active_allowed": name_owned and not third_party_app,
        # IP-level scanning (ports): owned IP and not a shared CDN address. When no
        # ranges are declared, fall back to "any non-CDN IP".
        "port_scan_allowed": (not on_cdn) and (ip_owned or not owned_cidrs),
    }
