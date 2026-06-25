"""Best-effort CVE lookup against the public NVD API.

Given the technologies/version strings fingerprinted during enrichment, this
queries the NVD CVE feed by keyword (product + version) and returns matching
CVEs with CVSS severity. Matching is intentionally best-effort — results are a
starting point for triage, not authoritative, and are flagged as such.

Runs only on the manual per-subdomain scan, so query volume is low. Responses
are cached in-process to avoid repeat calls (NVD rate-limits unauthenticated
clients); set an NVD API key to raise the limit.
"""
import asyncio
import logging
import re
import time
from typing import Dict, List, Optional, Tuple

import aiohttp

logger = logging.getLogger(__name__)

NVD_URL = "https://services.nvd.nist.gov/rest/json/2.0/cves/2.0"
_CACHE_TTL = 3600  # seconds
_cache: Dict[str, Tuple[float, list]] = {}
# Serialize NVD calls + small delay to stay under the unauthenticated rate limit.
_lock = asyncio.Lock()

# product/version like "nginx/1.18.0" or "Apache/2.4.41 (Ubuntu)"
_SERVER_RE = re.compile(r"^([A-Za-z][\w .+-]*?)[/ ]v?(\d+(?:\.\d+){1,3})")
_VERSION_IN_TECH = re.compile(r"^(.*?)[ /]v?(\d+(?:\.\d+){1,3})$")


def extract_products(web_server: Optional[str], technologies: List[str]) -> List[Tuple[str, str]]:
    """Derive (product, version) candidates from enrichment output.

    Only emits candidates that carry a version — versionless tech is too noisy
    for a keyword CVE search.
    """
    out: List[Tuple[str, str]] = []
    seen = set()

    def add(product: str, version: str):
        product = product.strip()
        key = (product.lower(), version)
        if product and key not in seen:
            seen.add(key)
            out.append((product, version))

    if web_server:
        m = _SERVER_RE.match(web_server.strip())
        if m:
            add(m.group(1), m.group(2))
    for tech in technologies or []:
        m = _VERSION_IN_TECH.match(tech.strip())
        if m:
            add(m.group(1), m.group(2))
    return out


def _severity_rank(sev: str) -> int:
    return {"CRITICAL": 4, "HIGH": 3, "MEDIUM": 2, "LOW": 1, "NONE": 0}.get((sev or "").upper(), 0)


def _parse_cve(item: dict) -> Optional[dict]:
    cve = item.get("cve", {})
    cve_id = cve.get("id")
    if not cve_id:
        return None
    descs = cve.get("descriptions", [])
    summary = next((d.get("value") for d in descs if d.get("lang") == "en"), "")
    score, severity = None, "UNKNOWN"
    metrics = cve.get("metrics", {})
    for key in ("cvssMetricV31", "cvssMetricV30", "cvssMetricV2"):
        arr = metrics.get(key)
        if arr:
            data = arr[0].get("cvssData", {})
            score = data.get("baseScore")
            severity = data.get("baseSeverity") or arr[0].get("baseSeverity") or "UNKNOWN"
            break
    return {
        "cve_id": cve_id,
        "cvss": score,
        "severity": (severity or "UNKNOWN").upper(),
        "summary": (summary or "")[:500],
    }


async def _query_nvd(session: aiohttp.ClientSession, keyword: str, api_key: Optional[str]) -> list:
    cached = _cache.get(keyword)
    if cached and (time.time() - cached[0]) < _CACHE_TTL:
        return cached[1]

    headers = {"apiKey": api_key} if api_key else {}
    params = {"keywordSearch": keyword, "resultsPerPage": 20}
    async with _lock:
        try:
            async with session.get(NVD_URL, params=params, headers=headers) as resp:
                if resp.status != 200:
                    logger.warning("NVD returned %s for %r", resp.status, keyword)
                    _cache[keyword] = (time.time(), [])
                    return []
                data = await resp.json(content_type=None)
        except Exception as e:
            logger.warning("NVD query failed for %r: %s", keyword, e)
            return []
        # Be polite to the rate limiter between distinct calls.
        await asyncio.sleep(0.8 if api_key else 6.0)

    out = []
    for item in (data or {}).get("vulnerabilities", []):
        parsed = _parse_cve(item)
        if parsed:
            out.append(parsed)
    _cache[keyword] = (time.time(), out)
    return out


async def lookup(
    web_server: Optional[str],
    technologies: List[str],
    api_key: Optional[str] = None,
    max_per_product: int = 5,
) -> List[dict]:
    """Return de-duplicated CVE findings for a host's fingerprinted software.

    Each finding includes the matched product/version so the operator can judge
    relevance (best-effort keyword match).
    """
    candidates = extract_products(web_server, technologies)
    if not candidates:
        return []

    findings: Dict[str, dict] = {}
    timeout = aiohttp.ClientTimeout(total=30)
    async with aiohttp.ClientSession(timeout=timeout, headers={"User-Agent": "korug-recon/1.0"}) as session:
        for product, version in candidates:
            cves = await _query_nvd(session, f"{product} {version}", api_key)
            # Keep the most severe matches that actually mention the version.
            relevant = [c for c in cves if version in (c["summary"] or "")] or cves
            relevant.sort(key=lambda c: (_severity_rank(c["severity"]), c["cvss"] or 0), reverse=True)
            for c in relevant[:max_per_product]:
                entry = dict(c)
                entry["product"] = product
                entry["version"] = version
                findings[c["cve_id"]] = entry  # de-dup by CVE id

    return list(findings.values())
