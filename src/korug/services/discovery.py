"""Passive subdomain discovery from many sources.

Aggregates subdomains from free (no-key) third-party sources plus optional
key-gated providers and the local Subfinder/Amass tools. Every source is
best-effort: failures are logged and skipped so one bad source never fails a
scan. DNS resolution and probing live in ``enrichment.py``.
"""
import asyncio
import json
import logging
import re
import subprocess
from typing import Dict, Set

import aiohttp

from korug.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

# Valid hostname label characters; used to clean source output.
_HOST_RE = re.compile(r"^[a-z0-9._-]+$")


def _clean(name: str, domain: str) -> str | None:
    """Normalize a candidate hostname; return None if it isn't a subdomain."""
    if not name:
        return None
    name = name.strip().lower().rstrip(".")
    name = name.removeprefix("*.")
    if "@" in name or "/" in name:
        return None
    if not _HOST_RE.match(name):
        return None
    if name == domain or name.endswith("." + domain):
        return name
    return None


class DiscoveryService:
    """Discover subdomains from local tools and passive web sources."""

    def __init__(self):
        self.subfinder_path = settings.subfinder_path
        self.amass_path = settings.amass_path

    async def discover(self, domain: str) -> Dict[str, Set[str]]:
        """Return a mapping of subdomain -> set of source names that found it."""
        found: Dict[str, Set[str]] = {}

        def merge(source: str, names: Set[str]):
            for raw in names:
                cleaned = _clean(raw, domain)
                if cleaned:
                    found.setdefault(cleaned, set()).add(source)

        timeout = aiohttp.ClientTimeout(total=settings.api_timeout)
        headers = {"User-Agent": "korug-recon/1.0"}
        async with aiohttp.ClientSession(timeout=timeout, headers=headers) as session:
            tasks = {
                "crt.sh": self._crtsh(session, domain),
                "hackertarget": self._hackertarget(session, domain),
                "certspotter": self._certspotter(session, domain),
                "rapiddns": self._rapiddns(session, domain),
                "alienvault": self._alienvault(session, domain),
                "threatminer": self._threatminer(session, domain),
                "wayback": self._wayback(session, domain),
                "bufferover": self._bufferover(session, domain),
                "threatcrowd": self._threatcrowd(session, domain),
            }
            # Key-gated sources
            if settings.virustotal_api_key:
                tasks["virustotal"] = self._virustotal(session, domain)
            if settings.securitytrails_api_key:
                tasks["securitytrails"] = self._securitytrails(session, domain)
            if settings.binaryedge_api_key:
                tasks["binaryedge"] = self._binaryedge(session, domain)
            if settings.urlscan_api_key:
                tasks["urlscan"] = self._urlscan(session, domain)

            results = await asyncio.gather(*tasks.values(), return_exceptions=True)
            for source, result in zip(tasks.keys(), results):
                if isinstance(result, Exception):
                    logger.warning("Source %s failed: %s", source, result)
                else:
                    merge(source, result)

        # Local CLI tools (subprocess, run off the event loop)
        merge("subfinder", await asyncio.to_thread(self._run_subfinder, domain))
        merge("amass", await asyncio.to_thread(self._run_amass, domain))
        if settings.shodan_api_key:
            merge("shodan", await asyncio.to_thread(self._query_shodan, domain))

        # Always include the apex domain itself.
        found.setdefault(domain, set()).add("seed")

        logger.info("Discovery for %s: %d unique names from %d sources",
                    domain, len(found), len({s for srcs in found.values() for s in srcs}))
        return found

    # Backwards-compatible wrapper (older callers expected a dict with DNS records).
    async def discover_subdomains(self, domain: str) -> dict:
        found = await self.discover(domain)
        return {"domain": domain, "total_discovered": len(found),
                "subdomains": {name: sorted(src) for name, src in found.items()}}

    # ---- Free HTTP sources -------------------------------------------------

    async def _get_json(self, session, url, **kw):
        async with session.get(url, **kw) as resp:
            if resp.status == 200:
                return await resp.json(content_type=None)
            return None

    async def _get_text(self, session, url, **kw):
        async with session.get(url, **kw) as resp:
            if resp.status == 200:
                return await resp.text()
            return None

    async def _crtsh(self, session, domain) -> Set[str]:
        data = await self._get_json(session, f"https://crt.sh/?q=%25.{domain}&output=json")
        out: Set[str] = set()
        for row in data or []:
            for field in (row.get("name_value", ""), row.get("common_name", "")):
                for line in field.split("\n"):
                    out.add(line)
        return out

    async def _hackertarget(self, session, domain) -> Set[str]:
        text = await self._get_text(session, f"https://api.hackertarget.com/hostsearch/?q={domain}")
        out: Set[str] = set()
        if text and "error" not in text.lower() and "exceeded" not in text.lower():
            for line in text.splitlines():
                out.add(line.split(",")[0])
        return out

    async def _certspotter(self, session, domain) -> Set[str]:
        url = (f"https://api.certspotter.com/v1/issuances?domain={domain}"
               "&include_subdomains=true&expand=dns_names")
        data = await self._get_json(session, url)
        out: Set[str] = set()
        for cert in data or []:
            out.update(cert.get("dns_names", []))
        return out

    async def _rapiddns(self, session, domain) -> Set[str]:
        text = await self._get_text(session, f"https://rapiddns.io/subdomain/{domain}?full=1")
        if not text:
            return set()
        return set(re.findall(rf"[a-z0-9._-]+\.{re.escape(domain)}", text.lower()))

    async def _alienvault(self, session, domain) -> Set[str]:
        url = f"https://otx.alienvault.com/api/v1/indicators/domain/{domain}/passive_dns"
        data = await self._get_json(session, url)
        return {r.get("hostname", "") for r in (data or {}).get("passive_dns", [])}

    async def _threatminer(self, session, domain) -> Set[str]:
        data = await self._get_json(session, f"https://api.threatminer.org/v2/domain.php?q={domain}&rt=5")
        return set((data or {}).get("results", []))

    async def _wayback(self, session, domain) -> Set[str]:
        url = (f"http://web.archive.org/cdx/search/cdx?url=*.{domain}/*"
               "&output=text&fl=original&collapse=urlkey&limit=10000")
        text = await self._get_text(session, url)
        out: Set[str] = set()
        for line in (text or "").splitlines():
            m = re.search(r"https?://([^/]+)/?", line)
            if m:
                out.add(m.group(1).split(":")[0])
        return out

    async def _bufferover(self, session, domain) -> Set[str]:
        data = await self._get_json(session, f"https://dns.bufferover.run/dns?q=.{domain}")
        out: Set[str] = set()
        for key in ("FDNS_A", "RDNS"):
            for row in (data or {}).get(key, []) or []:
                out.add(row.split(",")[-1])
        return out

    async def _threatcrowd(self, session, domain) -> Set[str]:
        url = f"https://www.threatcrowd.org/searchApi/v2/domain/report/?domain={domain}"
        data = await self._get_json(session, url)
        return set((data or {}).get("subdomains", []))

    # ---- Key-gated HTTP sources -------------------------------------------

    async def _virustotal(self, session, domain) -> Set[str]:
        url = f"https://www.virustotal.com/api/v3/domains/{domain}/subdomains?limit=1000"
        headers = {"x-apikey": settings.virustotal_api_key}
        data = await self._get_json(session, url, headers=headers)
        return {item.get("id", "") for item in (data or {}).get("data", [])}

    async def _securitytrails(self, session, domain) -> Set[str]:
        url = f"https://api.securitytrails.com/v1/domain/{domain}/subdomains"
        headers = {"APIKEY": settings.securitytrails_api_key}
        data = await self._get_json(session, url, headers=headers)
        return {f"{p}.{domain}" for p in (data or {}).get("subdomains", [])}

    async def _binaryedge(self, session, domain) -> Set[str]:
        url = f"https://api.binaryedge.io/v2/query/domains/subdomain/{domain}"
        headers = {"X-Key": settings.binaryedge_api_key}
        data = await self._get_json(session, url, headers=headers)
        return set((data or {}).get("events", []))

    async def _urlscan(self, session, domain) -> Set[str]:
        url = f"https://urlscan.io/api/v1/search/?q=domain:{domain}&size=1000"
        headers = {"API-Key": settings.urlscan_api_key}
        data = await self._get_json(session, url, headers=headers)
        return {r.get("page", {}).get("domain", "") for r in (data or {}).get("results", [])}

    # ---- Local CLI tools ---------------------------------------------------

    def _run_subfinder(self, domain: str) -> Set[str]:
        results: Set[str] = set()
        try:
            r = subprocess.run([self.subfinder_path, "-d", domain, "-silent"],
                               capture_output=True, text=True, timeout=120)
            if r.returncode == 0:
                results.update(l.strip() for l in r.stdout.splitlines() if l.strip())
        except FileNotFoundError:
            logger.warning("Subfinder not found at %s", self.subfinder_path)
        except Exception as e:
            logger.warning("Subfinder error: %s", e)
        return results

    def _run_amass(self, domain: str) -> Set[str]:
        results: Set[str] = set()
        try:
            r = subprocess.run([self.amass_path, "enum", "-passive", "-d", domain, "-norecursive"],
                               capture_output=True, text=True, timeout=180)
            if r.returncode == 0:
                for line in r.stdout.splitlines():
                    parts = line.split()
                    if parts:
                        results.add(parts[-1])
        except FileNotFoundError:
            logger.warning("Amass not found at %s", self.amass_path)
        except Exception as e:
            logger.warning("Amass error: %s", e)
        return results

    def _query_shodan(self, domain: str) -> Set[str]:
        results: Set[str] = set()
        try:
            import shodan
            api = shodan.Shodan(settings.shodan_api_key)
            res = api.search(f"hostname:{domain}")
            for match in res.get("matches", []):
                results.update(match.get("hostnames", []))
        except Exception as e:
            logger.warning("Shodan error: %s", e)
        return results


discovery_service = DiscoveryService()
