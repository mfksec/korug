"""Active, template-based vulnerability scanning via the nuclei CLI.

Wraps `nuclei <https://github.com/projectdiscovery/nuclei>`_ (ProjectDiscovery) to
run templated checks — subdomain takeover, known CVEs, exposed panels/files,
misconfigurations, default logins — against live hosts. nuclei handles its own
concurrency and rate limiting, so we invoke it **once** over the whole target
batch rather than per host.

This is active and intrusive: callers gate it to domains in "active" monitor mode
and to authorized targets. Best-effort — a missing binary, timeout, or parse error
yields no findings rather than failing a scan.
"""
import asyncio
import json
import logging
import subprocess
from typing import Dict, List, Optional
from urllib.parse import urlparse

from korug.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

# nuclei severity → 0-100 confidence used across Körüg's vulnerability model.
_SEVERITY_CONFIDENCE = {
    "critical": 95.0, "high": 85.0, "medium": 65.0, "low": 45.0,
    "info": 20.0, "unknown": 30.0,
}


def severity_confidence(severity: Optional[str]) -> float:
    return _SEVERITY_CONFIDENCE.get((severity or "").lower(), 30.0)


def host_of(value: Optional[str]) -> Optional[str]:
    """Normalize a nuclei host/matched-at value to a bare lowercase hostname."""
    if not value:
        return None
    v = value.strip()
    if "://" in v:
        parsed = urlparse(v)
        v = parsed.netloc or parsed.path
    v = v.split("/")[0].split(":")[0]  # drop any path then port
    return v.lower() or None


def parse_jsonl(output: str) -> List[Dict]:
    """Parse nuclei ``-jsonl`` output into normalized finding dicts."""
    findings: List[Dict] = []
    for line in (output or "").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            row = json.loads(line)
        except (ValueError, TypeError):
            continue
        info = row.get("info") or {}
        template_id = row.get("template-id") or row.get("templateID")
        if not template_id:
            continue
        host = host_of(row.get("host") or row.get("matched-at") or row.get("matched_at"))
        findings.append({
            "template_id": template_id,
            "name": info.get("name") or template_id,
            "severity": (info.get("severity") or "unknown").lower(),
            "description": (info.get("description") or "").strip()[:500],
            "matched_at": row.get("matched-at") or row.get("matched_at"),
            "type": row.get("type"),
            "host": host,
        })
    return findings


async def scan(
    urls: List[str],
    *,
    tags: Optional[str] = None,
    severities: Optional[str] = None,
    rate_limit: Optional[int] = None,
    timeout: Optional[int] = None,
) -> List[Dict]:
    """Run nuclei over ``urls`` and return normalized findings (each has ``host``).

    Targets are fed on stdin; nuclei scans them concurrently. Returns ``[]`` on a
    missing binary or any failure.
    """
    targets = [u for u in (urls or []) if u]
    if not targets:
        return []

    tags = tags if tags is not None else settings.nuclei_tags
    severities = severities if severities is not None else settings.nuclei_severity
    rate_limit = rate_limit if rate_limit is not None else settings.nuclei_rate_limit
    timeout = timeout if timeout is not None else settings.nuclei_timeout

    cmd = [
        settings.nuclei_path, "-silent", "-jsonl", "-disable-update-check",
        "-no-color", "-rate-limit", str(rate_limit),
    ]
    if tags:
        cmd += ["-tags", tags]
    if severities:
        cmd += ["-severity", severities]

    def _run() -> str:
        proc = subprocess.run(
            cmd, input="\n".join(targets),
            capture_output=True, text=True, timeout=timeout,
        )
        return proc.stdout

    try:
        output = await asyncio.to_thread(_run)
    except FileNotFoundError:
        logger.warning("nuclei not found at %s — skipping active scan", settings.nuclei_path)
        return []
    except subprocess.TimeoutExpired:
        logger.warning("nuclei timed out after %ss over %d target(s)", timeout, len(targets))
        return []
    except Exception as e:
        logger.warning("nuclei run failed: %s", e)
        return []

    findings = parse_jsonl(output)
    logger.info("nuclei: %d finding(s) across %d target(s)", len(findings), len(targets))
    return findings
