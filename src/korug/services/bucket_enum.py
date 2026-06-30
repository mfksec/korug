"""Public cloud storage (bucket) enumeration.

Derives candidate bucket / storage-account names from a domain's keyword
(e.g. ``example`` -> ``example-backups``, ``examplestatic`` ...) and probes the
well-known public endpoints for AWS S3, Google Cloud Storage, and Azure Blob
Storage. A bucket that exists is informative; one that lists its contents
publicly is a real exposure finding.

These are plain HTTP probes to public endpoints — no external binary and no
credentials are needed — so this runs natively on aiohttp rather than shelling
out. The permutation approach is inspired by **cloud_enum** (initstring) and
**S3Scanner** (sa7mon); see the Acknowledgements in the README.

Probing third-party object stores is active reconnaissance, so callers gate it
to domains in "active" monitor mode and make it opt-in (``enable_bucket_enum``).
Best-effort: network errors are swallowed per-probe.
"""
import asyncio
import logging
from typing import Dict, List, Optional

import aiohttp

from korug.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

# Second-level labels that precede a country-code TLD (example.co.uk), so the
# keyword extraction drops both labels rather than just the final one.
_SLD_BEFORE_CCTLD = {"co", "com", "org", "net", "gov", "ac", "edu"}

# Common environment/purpose affixes combined with the keyword to guess names.
_AFFIXES = [
    "dev", "development", "staging", "stage", "prod", "production", "test",
    "qa", "backup", "backups", "assets", "static", "media", "uploads", "files",
    "data", "db", "logs", "log", "public", "private", "internal", "cdn",
    "images", "img", "web", "app", "api", "storage", "archive", "bucket", "s3",
]

_MAX_NAMES = 150  # cap candidate names so a scan can't explode into thousands of probes


def keyword_from_domain(domain: str) -> str:
    """Extract the registrable keyword from a domain (``example.co.uk`` -> ``example``)."""
    labels = [l for l in (domain or "").strip().lower().rstrip(".").split(".") if l]
    if not labels:
        return ""
    # Drop the TLD; drop a second label too for co.uk-style ccTLDs.
    if len(labels) >= 3 and len(labels[-1]) == 2 and labels[-2] in _SLD_BEFORE_CCTLD:
        labels = labels[:-2]
    elif len(labels) >= 2:
        labels = labels[:-1]
    return labels[-1] if labels else ""


def generate_bucket_names(keyword: str) -> List[str]:
    """Generate candidate bucket names from a keyword (deduped, order-stable, bounded).

    Produces the bare keyword plus ``keyword<sep>affix`` and ``affix<sep>keyword``
    permutations for ``-`` and ``.`` separators.
    """
    kw = "".join(c for c in (keyword or "").strip().lower() if c.isalnum() or c == "-")
    if not kw:
        return []
    seen = set()
    names: List[str] = []

    def add(name: str) -> None:
        if name and name not in seen and len(name) <= 63:
            seen.add(name)
            names.append(name)

    add(kw)
    for affix in _AFFIXES:
        for sep in ("-", "."):
            add(f"{kw}{sep}{affix}")
            add(f"{affix}{sep}{kw}")
        add(f"{kw}{affix}")  # also the no-separator concatenation
    return names[:_MAX_NAMES]


def azure_account(name: str) -> Optional[str]:
    """Normalize a candidate to a valid Azure storage account name, or None.

    Azure account names are 3-24 chars, lowercase letters and digits only.
    """
    acct = "".join(c for c in (name or "").lower() if c.isalnum())
    return acct if 3 <= len(acct) <= 24 else None


def candidate_urls(name: str) -> List[Dict[str, str]]:
    """Build the provider probe URLs for a candidate name.

    Returns a list of ``{provider, bucket, url}``. Azure is only included when the
    name yields a valid account name.
    """
    probes = [
        {"provider": "s3", "bucket": name,
         "url": f"https://{name}.s3.amazonaws.com/"},
        {"provider": "gcs", "bucket": name,
         "url": f"https://storage.googleapis.com/{name}/"},
    ]
    acct = azure_account(name)
    if acct:
        probes.append({
            "provider": "azure", "bucket": acct,
            # List the default container; account existence + public listing both fall out.
            "url": f"https://{acct}.blob.core.windows.net/?comp=list",
        })
    return probes


def classify_response(provider: str, status: int, body: str) -> Dict:
    """Interpret a probe response into ``{exists, public}`` for the provider.

    ``public`` means the store returned a successful directory listing; ``exists``
    means it's present but access was denied. Unknown/404 statuses are neither.
    """
    body = body or ""
    exists = public = False
    if provider in ("s3", "gcs"):
        if status == 200:
            exists = public = True
        elif status == 403:           # AccessDenied / forbidden -> present but private
            exists = True
        elif status == 401:
            exists = True
    elif provider == "azure":
        if status == 200 and "EnumerationResults" in body:
            exists = public = True
        elif status in (403, 409):     # account exists, listing not public
            exists = True
        elif status == 400 and "PublicAccessNotPermitted" in body:
            exists = True
    return {"exists": exists, "public": public}


async def _probe(session, probe: Dict) -> Optional[Dict]:
    """Probe one bucket URL; return a finding dict if the bucket exists, else None."""
    try:
        async with session.get(probe["url"], allow_redirects=False) as resp:
            # Only the opening bytes are needed to spot a listing.
            body = (await resp.text(errors="ignore"))[:2048]
            verdict = classify_response(probe["provider"], resp.status, body)
    except Exception:
        return None
    if not verdict["exists"]:
        return None
    return {
        "provider": probe["provider"],
        "bucket": probe["bucket"],
        "url": probe["url"],
        "public": verdict["public"],
    }


async def enumerate_buckets(domain: str) -> List[Dict]:
    """Enumerate likely public buckets for ``domain``; return existing-bucket findings.

    Concurrency-capped and best-effort. Each finding is
    ``{provider, bucket, url, public}``; ``public`` flags an open listing.
    """
    keyword = keyword_from_domain(domain)
    names = generate_bucket_names(keyword)
    if not names:
        return []

    probes: List[Dict] = []
    for name in names:
        probes.extend(candidate_urls(name))

    sem = asyncio.Semaphore(settings.enrichment_concurrency)
    timeout = aiohttp.ClientTimeout(total=settings.http_probe_timeout)
    headers = {"User-Agent": "korug-recon/1.0"}

    async def guarded(session, probe):
        async with sem:
            return await _probe(session, probe)

    async with aiohttp.ClientSession(timeout=timeout, headers=headers) as session:
        results = await asyncio.gather(*(guarded(session, p) for p in probes))

    findings = [r for r in results if r]
    logger.info("bucket enum for %s: %d existing bucket(s) (%d public) from %d probe(s)",
                domain, len(findings), sum(1 for f in findings if f["public"]), len(probes))
    return findings
