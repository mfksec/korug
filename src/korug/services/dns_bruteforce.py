"""Active subdomain brute-forcing via massdns.

massdns <https://github.com/blechschmidt/massdns> resolves a very large list of
candidate names against a pool of public resolvers at high speed. We turn a
wordlist into ``<word>.<domain>`` candidates, resolve them all in one massdns
run, and return the names that actually resolve — a discovery source that finds
hosts no passive data source ever indexed.

This is active (it generates real DNS queries for guessed names) and depends on
operator-supplied inputs (a wordlist and a resolvers file), so it is opt-in
(``enable_massdns``) and disabled unless both files are configured. Best-effort:
a missing binary, missing wordlist/resolvers, timeout, or parse error yields no
names rather than failing discovery.
"""
import logging
import subprocess
from typing import List, Set

from korug.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


def parse_massdns_simple(output: str) -> Set[str]:
    """Parse massdns ``-o S`` (simple) output into a set of resolving hostnames.

    Lines look like ``sub.example.com. A 93.184.216.34`` or
    ``sub.example.com. CNAME other.example.com.``. We take the queried name
    (first field), strip the trailing dot, and lowercase it. NXDOMAIN/empty
    answers don't appear in simple output, so any line here resolved.
    """
    names: Set[str] = set()
    for line in (output or "").splitlines():
        line = line.strip()
        if not line:
            continue
        parts = line.split()
        if len(parts) < 3:
            continue
        name = parts[0].rstrip(".").lower()
        if name:
            names.add(name)
    return names


def generate_candidates(domain: str, words: List[str]) -> List[str]:
    """Build ``<word>.<domain>`` FQDNs from a wordlist (deduped, order-stable)."""
    domain = (domain or "").strip().lower().rstrip(".")
    if not domain:
        return []
    seen: Set[str] = set()
    candidates: List[str] = []
    for raw in words:
        w = (raw or "").strip().lower().strip(".")
        if not w or "/" in w or "*" in w:
            continue
        fqdn = f"{w}.{domain}"
        if fqdn not in seen:
            seen.add(fqdn)
            candidates.append(fqdn)
    return candidates


def load_words(path: str) -> List[str]:
    """Read a wordlist file into a list of words. Best-effort: ``[]`` on any error."""
    if not path:
        return []
    try:
        with open(path, "r", encoding="utf-8", errors="ignore") as fh:
            return [line.strip() for line in fh if line.strip() and not line.startswith("#")]
    except OSError as e:
        logger.warning("massdns wordlist unreadable (%s): %s", path, e)
        return []


def run(domain: str) -> Set[str]:
    """Brute-force subdomains of ``domain`` with massdns; return resolving names.

    Synchronous so discovery can run it off the event loop via ``to_thread``
    alongside the other CLI sources. Returns ``set()`` when disabled, when the
    wordlist/resolvers aren't configured, or on any failure.
    """
    wordlist = settings.massdns_wordlist
    resolvers = settings.massdns_resolvers
    if not wordlist or not resolvers:
        logger.info("massdns enabled but wordlist/resolvers not configured — skipping")
        return set()

    words = load_words(wordlist)
    candidates = generate_candidates(domain, words)
    if not candidates:
        return set()

    # -r resolvers, -t A record type, -o S simple output, -q quiet; names on stdin.
    cmd = [settings.massdns_path, "-r", resolvers, "-t", "A", "-o", "S", "-q"]
    try:
        proc = subprocess.run(
            cmd, input="\n".join(candidates),
            capture_output=True, text=True, timeout=settings.massdns_timeout,
        )
    except FileNotFoundError:
        logger.warning("massdns not found at %s — skipping brute-force", settings.massdns_path)
        return set()
    except subprocess.TimeoutExpired:
        logger.warning("massdns timed out after %ss over %d candidate(s)",
                       settings.massdns_timeout, len(candidates))
        return set()
    except Exception as e:
        logger.warning("massdns run failed: %s", e)
        return set()

    names = parse_massdns_simple(proc.stdout)
    logger.info("massdns: %d resolving name(s) from %d candidate(s)", len(names), len(candidates))
    return names
