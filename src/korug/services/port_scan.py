"""Fast port discovery via a masscan -> nmap pipeline.

masscan <https://github.com/robertdavidgraham/masscan> sweeps a wide port range
at high speed to find *which* ports are open; nmap
<https://nmap.org> then runs service/version detection (`-sV`) against just those
open ports. This two-stage split is far faster than asking nmap to probe a wide
range directly, and yields the same ``{port, proto, service?, product?, version?}``
shape the rest of Körüg already consumes.

Both stages are active and IP-level intrusive, so callers gate them on the
IP-ownership rule ("scope is law": never scan a shared CDN IP; honour declared
owned ranges). masscan needs raw-socket privileges (typically root or
``CAP_NET_RAW``); when it is missing or unprivileged this pipeline is best-effort
and the caller falls back to the simpler nmap/TCP-connect scan.
"""
import asyncio
import logging
import subprocess
from typing import List

from korug.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


def parse_masscan_list(output: str) -> List[int]:
    """Parse masscan ``-oL`` (list) output into sorted, unique open TCP ports.

    Lines look like ``open tcp 443 10.0.0.1 1700000000``; comment lines start
    with ``#``. The list format is line-oriented and far more robust to parse
    than masscan's quasi-JSON.
    """
    ports: set[int] = set()
    for line in (output or "").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        parts = line.split()
        # "open" "tcp" "<port>" "<ip>" "<timestamp>"
        if len(parts) >= 4 and parts[0] == "open" and parts[1] == "tcp":
            try:
                ports.add(int(parts[2]))
            except ValueError:
                continue
    return sorted(ports)


def parse_nmap_xml(xml_str: str) -> List[dict]:
    """Parse nmap ``-oX`` output into a list of open-port dicts.

    Shared by the masscan->nmap pipeline and the enrichment fallback scan.
    """
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


def _run_masscan(ip: str) -> List[int]:
    """Synchronously run masscan over ``ip`` and return open TCP ports."""
    cmd = [
        settings.masscan_path, ip, "-p", str(settings.masscan_ports),
        "--rate", str(settings.masscan_rate), "-oL", "-", "--wait", "0",
    ]
    proc = subprocess.run(
        cmd, capture_output=True, text=True, timeout=settings.masscan_timeout
    )
    return parse_masscan_list(proc.stdout)


def _run_nmap_services(ip: str, ports: List[int]) -> List[dict]:
    """Synchronously run nmap service detection over a specific port list."""
    port_csv = ",".join(str(p) for p in ports)
    cmd = [settings.nmap_path, "-Pn", "--open", "-T4"]
    if settings.nmap_service_detection:
        cmd.append("-sV")
    cmd += ["-p", port_csv, "-oX", "-", ip]
    proc = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
    return parse_nmap_xml(proc.stdout)


async def discover_and_detect(ip: str) -> List[dict]:
    """masscan-discover open ports on ``ip``, then nmap service-detect them.

    Returns the open-port dicts, or ``[]`` if masscan finds nothing or is missing.
    Best-effort and fully fault-isolated: a missing binary, lack of raw-socket
    privilege, timeout, or parse error yields ``[]`` so the caller can fall back.
    """
    try:
        open_ports = await asyncio.to_thread(_run_masscan, ip)
    except FileNotFoundError:
        logger.warning("masscan not found at %s — falling back", settings.masscan_path)
        return []
    except subprocess.TimeoutExpired:
        logger.warning("masscan timed out for %s", ip)
        return []
    except Exception as e:
        logger.warning("masscan failed for %s (%s) — falling back", ip, e)
        return []

    if not open_ports:
        return []

    # Service/version detection on just the discovered ports.
    try:
        detected = await asyncio.to_thread(_run_nmap_services, ip, open_ports)
        if detected:
            return detected
    except Exception as e:
        logger.warning("nmap service detection failed for %s (%s)", ip, e)

    # masscan found ports but nmap didn't enrich them — still report them.
    return [{"port": p, "proto": "tcp"} for p in open_ports]
