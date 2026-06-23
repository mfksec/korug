"""Enrichment for discovered subdomains.

For each candidate hostname this resolves DNS, optionally probes HTTP(S)
(with automatic https->http fallback), fingerprints basic technologies,
flags Cloudflare-fronted hosts, and optionally runs a bounded TCP port scan.
Everything runs concurrently with a semaphore cap and is best-effort.
"""
import asyncio
import ipaddress
import logging
import re
from dataclasses import dataclass, field
from typing import Dict, List, Optional

import aiohttp

from korug.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

# Cloudflare published IPv4 ranges (https://www.cloudflare.com/ips/).
_CLOUDFLARE_NETS = [ipaddress.ip_network(c) for c in (
    "173.245.48.0/20", "103.21.244.0/22", "103.22.200.0/22", "103.31.4.0/22",
    "141.101.64.0/18", "108.162.192.0/18", "190.93.240.0/20", "188.114.96.0/20",
    "197.234.240.0/22", "198.41.128.0/17", "162.158.0.0/15", "104.16.0.0/13",
    "104.24.0.0/14", "172.64.0.0/13", "131.0.72.0/22",
)]

_TITLE_RE = re.compile(r"<title[^>]*>(.*?)</title>", re.IGNORECASE | re.DOTALL)
_GENERATOR_RE = re.compile(r'<meta[^>]+name=["\']generator["\'][^>]+content=["\']([^"\']+)', re.I)


def is_cloudflare_ip(ip: str) -> bool:
    """True if the IPv4 address falls in a Cloudflare range."""
    try:
        addr = ipaddress.ip_address(ip)
    except ValueError:
        return False
    return any(addr in net for net in _CLOUDFLARE_NETS)


def detect_technologies(headers: dict, body: str) -> List[str]:
    """Lightweight technology fingerprinting from headers and HTML body."""
    tech: set[str] = set()
    server = headers.get("Server", "")
    powered = headers.get("X-Powered-By", "")
    if server:
        tech.add(server.split("/")[0].strip())
    if powered:
        tech.add(powered.split("/")[0].strip())
    if "cf-ray" in {k.lower() for k in headers}:
        tech.add("Cloudflare")
    low = body.lower()
    signatures = {
        "WordPress": "wp-content", "Drupal": "drupal-settings-json", "Joomla": "/media/jui/",
        "Next.js": "/_next/", "Nuxt.js": "__nuxt", "React": "data-reactroot",
        "Angular": "ng-version", "Vue.js": "data-v-", "Laravel": "laravel_session",
        "Shopify": "cdn.shopify.com", "Wix": "static.wixstatic.com",
    }
    for name, marker in signatures.items():
        if marker in low:
            tech.add(name)
    m = _GENERATOR_RE.search(body)
    if m:
        tech.add(m.group(1).split(" ")[0])
    return sorted(t for t in tech if t)


@dataclass
class EnrichResult:
    dns_records: dict = field(default_factory=lambda: {"A": [], "AAAA": [], "CNAME": None, "MX": [], "NS": []})
    resolved_ips: List[str] = field(default_factory=list)
    is_alive: bool = False
    status_code: Optional[int] = None
    final_url: Optional[str] = None
    http_title: Optional[str] = None
    content_length: Optional[int] = None
    web_server: Optional[str] = None
    technologies: List[str] = field(default_factory=list)
    open_ports: List[int] = field(default_factory=list)
    is_cloudflare: bool = False

    def resolved(self) -> bool:
        r = self.dns_records
        return bool(r["A"] or r["AAAA"] or r["CNAME"] or r["MX"] or r["NS"])


class EnrichmentService:
    """Resolve + probe + fingerprint + (optional) port-scan subdomains."""

    def __init__(self):
        self.concurrency = settings.enrichment_concurrency
        self.http_timeout = settings.http_probe_timeout
        self.ports = [int(p) for p in str(settings.port_scan_ports).split(",") if p.strip().isdigit()]

    async def enrich(self, names: List[str]) -> Dict[str, EnrichResult]:
        sem = asyncio.Semaphore(self.concurrency)
        timeout = aiohttp.ClientTimeout(total=self.http_timeout)
        connector = aiohttp.TCPConnector(ssl=False, limit=self.concurrency)
        async with aiohttp.ClientSession(timeout=timeout, connector=connector,
                                         headers={"User-Agent": "korug-recon/1.0"}) as session:
            async def run(name: str):
                async with sem:
                    return name, await self._enrich_one(session, name)
            pairs = await asyncio.gather(*(run(n) for n in names))
        return dict(pairs)

    async def _enrich_one(self, session, name: str) -> EnrichResult:
        result = EnrichResult()
        result.dns_records = await asyncio.to_thread(self._resolve, name)
        result.resolved_ips = list(result.dns_records["A"])
        result.is_cloudflare = any(is_cloudflare_ip(ip) for ip in result.resolved_ips)

        if not result.resolved():
            return result

        if settings.enable_http_probe:
            await self._probe(session, name, result)

        if settings.enable_port_scan and result.resolved_ips:
            result.open_ports = await self._scan_ports(result.resolved_ips[0])

        return result

    def _resolve(self, name: str) -> dict:
        import dns.resolver
        import dns.exception

        records = {"A": [], "AAAA": [], "CNAME": None, "MX": [], "NS": []}

        def q(rtype):
            try:
                ans = dns.resolver.resolve(name, rtype, raise_on_no_answer=False, lifetime=5)
                return list(ans) if ans.rrset is not None else []
            except (dns.exception.DNSException, Exception):
                return []

        records["A"] = [str(r) for r in q("A")]
        records["AAAA"] = [str(r) for r in q("AAAA")]
        cname = q("CNAME")
        if cname:
            records["CNAME"] = str(cname[0].target).rstrip(".")
        records["MX"] = [str(r.exchange).rstrip(".") for r in q("MX")]
        records["NS"] = [str(r.target).rstrip(".") for r in q("NS")]
        return records

    async def _probe(self, session, name: str, result: EnrichResult) -> None:
        """Try HTTPS, fall back to HTTP; capture status/title/server/tech."""
        for scheme in ("https", "http"):
            try:
                async with session.get(f"{scheme}://{name}", allow_redirects=True,
                                       max_redirects=5) as resp:
                    body = await resp.text(errors="ignore")
                    result.is_alive = True
                    result.status_code = resp.status
                    result.final_url = str(resp.url)
                    result.web_server = resp.headers.get("Server")
                    cl = resp.headers.get("Content-Length")
                    result.content_length = int(cl) if cl and cl.isdigit() else len(body)
                    m = _TITLE_RE.search(body)
                    if m:
                        result.http_title = re.sub(r"\s+", " ", m.group(1)).strip()[:500]
                    result.technologies = detect_technologies(dict(resp.headers), body)
                    return  # success on this scheme; don't try the next
            except Exception:
                continue  # try next scheme (smart https->http fallback)

    async def _scan_ports(self, host: str) -> List[int]:
        async def check(port: int) -> Optional[int]:
            try:
                fut = asyncio.open_connection(host, port)
                reader, writer = await asyncio.wait_for(fut, timeout=2)
                writer.close()
                try:
                    await writer.wait_closed()
                except Exception:
                    pass
                return port
            except Exception:
                return None

        results = await asyncio.gather(*(check(p) for p in self.ports))
        return sorted(p for p in results if p is not None)


enrichment_service = EnrichmentService()
