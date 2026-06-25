"""Passive subdomain discovery from many sources.

Aggregates subdomains from free (no-key) third-party sources plus optional
key-gated providers and the local Subfinder/Amass tools. Every source is
best-effort: failures are logged and skipped so one bad source never fails a
scan. DNS resolution and probing live in ``enrichment.py``.
"""
import asyncio
import logging
import re
import subprocess
from typing import Callable, Dict, Optional, Set

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

    async def discover(
        self,
        domain: str,
        should_cancel: Optional[Callable[[], bool]] = None,
        keys: Optional[Dict[str, str]] = None,
    ) -> Dict[str, Set[str]]:
        """Return a mapping of subdomain -> set of source names that found it.

        ``should_cancel`` is polled while sources run; when it returns True the
        in-flight source fetches are cancelled and discovery returns early with
        whatever was gathered so far. ``keys`` overrides the env-configured
        source API keys (e.g. ones set from the UI).
        """
        found: Dict[str, Set[str]] = {}
        k = self._effective_keys(keys)

        def merge(source: str, names: Set[str]):
            for raw in names:
                cleaned = _clean(raw, domain)
                if cleaned:
                    found.setdefault(cleaned, set()).add(source)

        timeout = aiohttp.ClientTimeout(total=settings.api_timeout)
        headers = {"User-Agent": "korug-recon/1.0"}
        async with aiohttp.ClientSession(timeout=timeout, headers=headers) as session:
            coros = {
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
            # Key-gated sources (keys from UI/DB override env defaults)
            if k["virustotal"]:
                coros["virustotal"] = self._virustotal(session, domain, k["virustotal"])
            if k["securitytrails"]:
                coros["securitytrails"] = self._securitytrails(session, domain, k["securitytrails"])
            if k["binaryedge"]:
                coros["binaryedge"] = self._binaryedge(session, domain, k["binaryedge"])
            if k["urlscan"]:
                coros["urlscan"] = self._urlscan(session, domain, k["urlscan"])
            if k["censys_id"] and k["censys_secret"]:
                coros["censys"] = self._censys(session, domain, k["censys_id"], k["censys_secret"])

            # Local CLI tools run concurrently with the HTTP sources (off the
            # event loop) so discovery time is max(sources) rather than the sum,
            # and they participate in the same cancellation poll below.
            # amass is opt-in: passive amass adds ~60s and yields little without
            # configured data sources, so it's off by default (set ENABLE_AMASS).
            if settings.enable_subfinder:
                coros["subfinder"] = asyncio.to_thread(self._run_subfinder, domain)
            if settings.enable_amass:
                coros["amass"] = asyncio.to_thread(self._run_amass, domain)
            if k["shodan"]:
                coros["shodan"] = asyncio.to_thread(self._query_shodan, domain, k["shodan"])

            names = list(coros.keys())
            tasks = [asyncio.create_task(c) for c in coros.values()]
            pending = set(tasks)
            cancelled = False
            while pending:
                _, pending = await asyncio.wait(pending, timeout=2)
                if should_cancel and should_cancel():
                    for t in pending:
                        t.cancel()
                    await asyncio.gather(*pending, return_exceptions=True)
                    cancelled = True
                    break
            for source, task in zip(names, tasks):
                if task.cancelled():
                    continue
                exc = task.exception()
                if exc is not None:
                    logger.warning("Source %s failed: %s", source, exc)
                else:
                    merge(source, task.result())

        if cancelled:
            logger.info("Discovery cancelled for %s after %d names", domain, len(found))
            return found

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

    def _effective_keys(self, override: Optional[Dict[str, str]]) -> Dict[str, str]:
        """Merge UI/DB-provided source API keys over the env-configured defaults."""
        o = override or {}
        return {
            "shodan": o.get("shodan") or settings.shodan_api_key or "",
            "virustotal": o.get("virustotal") or settings.virustotal_api_key or "",
            "securitytrails": o.get("securitytrails") or settings.securitytrails_api_key or "",
            "binaryedge": o.get("binaryedge") or settings.binaryedge_api_key or "",
            "urlscan": o.get("urlscan") or settings.urlscan_api_key or "",
            "censys_id": o.get("censys_id") or settings.censys_api_id or "",
            "censys_secret": o.get("censys_secret") or settings.censys_api_secret or "",
        }

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

    async def _virustotal(self, session, domain, api_key) -> Set[str]:
        url = f"https://www.virustotal.com/api/v3/domains/{domain}/subdomains?limit=1000"
        headers = {"x-apikey": api_key}
        data = await self._get_json(session, url, headers=headers)
        return {item.get("id", "") for item in (data or {}).get("data", [])}

    async def _securitytrails(self, session, domain, api_key) -> Set[str]:
        url = f"https://api.securitytrails.com/v1/domain/{domain}/subdomains"
        headers = {"APIKEY": api_key}
        data = await self._get_json(session, url, headers=headers)
        return {f"{p}.{domain}" for p in (data or {}).get("subdomains", [])}

    async def _binaryedge(self, session, domain, api_key) -> Set[str]:
        url = f"https://api.binaryedge.io/v2/query/domains/subdomain/{domain}"
        headers = {"X-Key": api_key}
        data = await self._get_json(session, url, headers=headers)
        return set((data or {}).get("events", []))

    async def _urlscan(self, session, domain, api_key) -> Set[str]:
        url = f"https://urlscan.io/api/v1/search/?q=domain:{domain}&size=1000"
        headers = {"API-Key": api_key}
        data = await self._get_json(session, url, headers=headers)
        return {r.get("page", {}).get("domain", "") for r in (data or {}).get("results", [])}

    async def _censys(self, session, domain, api_id, api_secret) -> Set[str]:
        """Censys Search v2 hosts API (HTTP basic auth with API id/secret)."""
        url = f"https://search.censys.io/api/v2/hosts/search?q={domain}&per_page=100"
        auth = aiohttp.BasicAuth(api_id, api_secret)
        out: Set[str] = set()
        async with session.get(url, auth=auth) as resp:
            if resp.status != 200:
                return out
            data = await resp.json(content_type=None)
        for hit in (data or {}).get("result", {}).get("hits", []):
            names = hit.get("names") or hit.get("dns", {}).get("names") or []
            out.update(names)
            if hit.get("name"):
                out.add(hit["name"])
        return out

    # ---- Local CLI tools ---------------------------------------------------

    def _run_subfinder(self, domain: str) -> Set[str]:
        results: Set[str] = set()
        try:
            r = subprocess.run([self.subfinder_path, "-d", domain, "-silent"],
                               capture_output=True, text=True, timeout=60)
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
            r = subprocess.run([self.amass_path, "enum", "-passive", "-d", domain, "-norecursive", "-timeout", "1"],
                               capture_output=True, text=True, timeout=90)
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

    def _query_shodan(self, domain: str, api_key: str) -> Set[str]:
        results: Set[str] = set()
        try:
            import shodan
            api = shodan.Shodan(api_key)
            res = api.search(f"hostname:{domain}")
            for match in res.get("matches", []):
                results.update(match.get("hostnames", []))
        except Exception as e:
            logger.warning("Shodan error: %s", e)
        return results


discovery_service = DiscoveryService()
