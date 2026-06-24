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
import shutil
import subprocess
from dataclasses import dataclass, field
from typing import Callable, Dict, List, Optional

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


def _parse_nmap_xml(xml_str: str) -> List[dict]:
    """Parse nmap -oX output into a list of open-port dicts."""
    ports: List[dict] = []
    if not xml_str:
        return ports
    try:
        # defusedxml guards against XXE / billion-laughs in untrusted XML.
        from defusedxml.ElementTree import fromstring
        root = fromstring(xml_str)
    except Exception:
        return ports
    for port in root.findall(".//host/ports/port"):
        state = port.find("state")
        if state is None or state.get("state") != "open":
            continue
        entry = {"port": int(port.get("portid")), "proto": port.get("protocol")}
        svc = port.find("service")
        if svc is not None:
            if svc.get("name"):
                entry["service"] = svc.get("name")
            if svc.get("product"):
                entry["product"] = svc.get("product")
            if svc.get("version"):
                entry["version"] = svc.get("version")
        ports.append(entry)
    return sorted(ports, key=lambda d: d["port"])


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
    open_ports: List[dict] = field(default_factory=list)  # [{port, service?, product?, version?}]
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

    async def enrich(
        self,
        names: List[str],
        port_scan: Optional[bool] = None,
        should_cancel: Optional[Callable[[], bool]] = None,
    ) -> Dict[str, EnrichResult]:
        """Enrich names. ``port_scan`` overrides the configured default when set.

        ``should_cancel`` is checked between batches so a long enrichment run can
        be stopped promptly; when it returns True we return whatever finished so
        far instead of processing the remaining names.
        """
        do_ports = settings.enable_port_scan if port_scan is None else port_scan
        sem = asyncio.Semaphore(self.concurrency)
        timeout = aiohttp.ClientTimeout(total=self.http_timeout)
        connector = aiohttp.TCPConnector(ssl=False, limit=self.concurrency)
        # Process in bounded batches so a very large name set doesn't schedule
        # tens of thousands of tasks at once.
        batch_size = max(self.concurrency * 5, 50)
        results: Dict[str, EnrichResult] = {}
        async with aiohttp.ClientSession(timeout=timeout, connector=connector,
                                         headers={"User-Agent": "korug-recon/1.0"}) as session:
            async def run(name: str):
                async with sem:
                    # Results are written as each name finishes so partial work
                    # is preserved and in-flight tasks can be cancelled promptly.
                    results[name] = await self._enrich_one(session, name, do_ports)

            cancelled = False
            for start in range(0, len(names), batch_size):
                if should_cancel and should_cancel():
                    cancelled = True
                    break
                batch = names[start:start + batch_size]
                pending = {asyncio.create_task(run(n)) for n in batch}
                # Poll for cancellation while the batch runs; on request, cancel
                # the in-flight tasks rather than waiting for them to finish.
                while pending:
                    done, pending = await asyncio.wait(pending, timeout=2)
                    if should_cancel and should_cancel():
                        for t in pending:
                            t.cancel()
                        await asyncio.gather(*pending, return_exceptions=True)
                        cancelled = True
                        pending = set()
                if cancelled:
                    break
            if cancelled:
                logger.info("Enrichment cancelled after enriching %d/%d names",
                            len(results), len(names))
        return results

    async def _enrich_one(self, session, name: str, do_ports: bool) -> EnrichResult:
        result = EnrichResult()
        result.dns_records = await asyncio.to_thread(self._resolve, name)
        result.resolved_ips = list(result.dns_records["A"])
        result.is_cloudflare = any(is_cloudflare_ip(ip) for ip in result.resolved_ips)

        if not result.resolved():
            return result

        if settings.enable_http_probe:
            await self._probe(session, name, result)

        if do_ports and result.resolved_ips:
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

    async def _scan_ports(self, host: str) -> List[dict]:
        """Port scan a host. Prefer nmap (service/version), else async TCP connect.

        Returns a list of dicts: {port, service?, product?, version?}.
        """
        if shutil.which(settings.nmap_path):
            try:
                return await asyncio.to_thread(self._nmap_scan, host)
            except Exception as e:
                logger.warning("nmap scan failed for %s (%s); using TCP fallback", host, e)
        return await self._tcp_connect_scan(host)

    def _nmap_scan(self, host: str) -> List[dict]:
        ports = ",".join(str(p) for p in self.ports)
        cmd = [settings.nmap_path, "-Pn", "--open", "-T4", "-p", ports]
        if settings.nmap_service_detection:
            cmd.append("-sV")
        cmd += ["-oX", "-", host]
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
        return _parse_nmap_xml(proc.stdout)

    async def _tcp_connect_scan(self, host: str) -> List[dict]:
        async def check(port: int) -> Optional[dict]:
            try:
                fut = asyncio.open_connection(host, port)
                _, writer = await asyncio.wait_for(fut, timeout=2)
                writer.close()
                try:
                    await writer.wait_closed()
                except Exception:
                    pass
                return {"port": port}
            except Exception:
                return None

        results = await asyncio.gather(*(check(p) for p in self.ports))
        return [r for r in sorted((x for x in results if x), key=lambda d: d["port"])]


enrichment_service = EnrichmentService()
