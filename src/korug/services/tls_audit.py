"""Active TLS/SSL configuration auditing via the tlsx CLI.

Wraps `tlsx <https://github.com/projectdiscovery/tlsx>`_ (ProjectDiscovery) to
connect to a host's TLS endpoint and report certificate and protocol problems:
expired / self-signed / hostname-mismatched / untrusted certificates, deprecated
protocol versions (SSLv3, TLS 1.0/1.1), and weak cipher suites. tlsx handles its
own concurrency, so we invoke it **once** over the whole target batch.

This is active (it opens TLS connections to the target), so callers gate it to
domains in "active" monitor mode and to hosts we're authorized to probe — the
same host-level scope gate as nuclei (``host_active_allowed``). Best-effort: a
missing binary, timeout, or parse error yields no findings rather than failing a
scan.

The audit is intentionally distinct from the crt.sh certificate *monitoring* in
``certificates.py``: that records issuance history passively from CT logs; this
evaluates the certificate and protocol the host actually *serves*.
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

# Deprecated/insecure protocol versions tlsx may report (normalized lowercase,
# non-alphanumerics stripped) → the issue id and 0-100 confidence we assign.
# Keys cover both tlsx's native form ("ssl30") and the human/openssl form
# ("sslv3", "tls10") so the table is tolerant of either input.
_WEAK_TLS_VERSIONS = {
    "ssl30": ("sslv3", 80.0), "sslv3": ("sslv3", 80.0),
    "ssl20": ("sslv2", 90.0), "sslv2": ("sslv2", 90.0),
    "tls10": ("tls10", 65.0),
    "tls11": ("tls11", 65.0),
}

# Substrings marking a cipher suite as weak (case-insensitive).
_WEAK_CIPHER_MARKERS = (
    "null", "export", "anon", "rc4", "des", "3des", "md5", "_cbc_sha",
)

# Per-issue confidence (0-100) for certificate trust problems.
_CERT_ISSUE_CONFIDENCE = {
    "expired-cert": 70.0,
    "self-signed-cert": 60.0,
    "hostname-mismatch": 65.0,
    "untrusted-cert": 65.0,
    "revoked-cert": 90.0,
    "expiring-soon": 40.0,
    "weak-cipher": 65.0,
}


def host_of(value: Optional[str]) -> Optional[str]:
    """Normalize a tlsx host value to a bare lowercase hostname."""
    if not value:
        return None
    v = value.strip()
    if "://" in v:
        parsed = urlparse(v)
        v = parsed.netloc or parsed.path
    v = v.split("/")[0].split(":")[0]  # drop any path then port
    return v.lower() or None


def _norm_version(value: Optional[str]) -> str:
    """Normalize a TLS-version string to its weak-version-table key (e.g. 'tls10')."""
    return "".join(c for c in (value or "").lower() if c.isalnum())


def is_weak_cipher(cipher: Optional[str]) -> bool:
    """True if a cipher-suite name contains a known-weak primitive."""
    c = (cipher or "").lower()
    if not c:
        return False
    # "des" alone matches "3des" too, which is intended (both weak).
    return any(m in c for m in _WEAK_CIPHER_MARKERS)


def assess(record: Dict, *, expiry_warning_days: int = 14) -> List[Dict]:
    """Derive TLS findings from one normalized tlsx record.

    Returns a list of ``{issue, severity_confidence, message}`` dicts; empty when
    the host's TLS configuration looks clean. ``severity_confidence`` is the same
    0-100 scale Körüg uses everywhere for the vulnerability model.
    """
    findings: List[Dict] = []

    def add(issue: str, message: str) -> None:
        findings.append({
            "issue": issue,
            "severity_confidence": _CERT_ISSUE_CONFIDENCE.get(issue, 50.0),
            "message": message,
        })

    # Certificate trust problems (tlsx reports these as booleans when probed).
    if record.get("expired"):
        add("expired-cert", "TLS certificate is expired")
    if record.get("self_signed"):
        add("self-signed-cert", "TLS certificate is self-signed")
    if record.get("mismatched"):
        add("hostname-mismatch", "TLS certificate does not match the hostname")
    if record.get("untrusted"):
        add("untrusted-cert", "TLS certificate chain is untrusted")
    if record.get("revoked"):
        add("revoked-cert", "TLS certificate has been revoked")

    # Near-expiry: tlsx may surface days-until-expiry directly; honour it when present.
    days_left = record.get("not_after_days")
    if isinstance(days_left, (int, float)) and 0 <= days_left <= expiry_warning_days:
        add("expiring-soon", f"TLS certificate expires in {int(days_left)} day(s)")

    # Deprecated protocol version.
    weak = _WEAK_TLS_VERSIONS.get(_norm_version(record.get("tls_version")))
    if weak:
        issue, conf = weak
        findings.append({
            "issue": issue,
            "severity_confidence": conf,
            "message": f"Host negotiates deprecated {record.get('tls_version')}",
        })

    # Weak cipher suite.
    if is_weak_cipher(record.get("cipher")):
        add("weak-cipher", f"Weak cipher suite negotiated: {record.get('cipher')}")

    return findings


def parse_jsonl(output: str) -> List[Dict]:
    """Parse tlsx ``-json`` output into normalized per-host records.

    tlsx field names vary across versions (snake_case vs camelCase, and the
    expiry field has had several names); we read the common aliases so the
    assessment stays version-tolerant.
    """
    records: List[Dict] = []
    for line in (output or "").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            row = json.loads(line)
        except (ValueError, TypeError):
            continue
        host = host_of(row.get("host") or row.get("input"))
        if not host:
            continue
        records.append({
            "host": host,
            "port": row.get("port"),
            "ip": row.get("ip"),
            "tls_version": row.get("tls_version") or row.get("version"),
            "cipher": row.get("cipher"),
            "expired": bool(row.get("expired")),
            "self_signed": bool(row.get("self_signed") or row.get("self-signed")),
            "mismatched": bool(row.get("mismatched")),
            "untrusted": bool(row.get("untrusted")),
            "revoked": bool(row.get("revoked")),
            "not_after": row.get("not_after") or row.get("notAfter"),
            "not_after_days": row.get("not_after_days") or row.get("expiry_days"),
        })
    return records


async def scan(
    hosts: List[str],
    *,
    timeout: Optional[int] = None,
) -> List[Dict]:
    """Run tlsx over ``hosts`` and return normalized records (each has ``host``).

    Targets are fed on stdin; tlsx scans them concurrently. Returns ``[]`` on a
    missing binary or any failure.
    """
    targets = [h for h in (hosts or []) if h]
    if not targets:
        return []

    timeout = timeout if timeout is not None else settings.tlsx_timeout

    # Probe flags request the cert-trust booleans + negotiated version/cipher.
    cmd = [
        settings.tlsx_path, "-silent", "-json", "-disable-update-check", "-no-color",
        "-tls-version", "-cipher", "-expired", "-self-signed", "-mismatched",
        "-untrusted", "-revoked",
    ]

    def _run() -> str:
        proc = subprocess.run(
            cmd, input="\n".join(targets),
            capture_output=True, text=True, timeout=timeout,
        )
        return proc.stdout

    try:
        output = await asyncio.to_thread(_run)
    except FileNotFoundError:
        logger.warning("tlsx not found at %s — skipping TLS audit", settings.tlsx_path)
        return []
    except subprocess.TimeoutExpired:
        logger.warning("tlsx timed out after %ss over %d host(s)", timeout, len(targets))
        return []
    except Exception as e:
        logger.warning("tlsx run failed: %s", e)
        return []

    records = parse_jsonl(output)
    logger.info("tlsx: audited %d host(s), %d record(s)", len(targets), len(records))
    return records
