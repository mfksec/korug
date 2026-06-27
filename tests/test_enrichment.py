"""Tests for the enrichment service (pure, deterministic helpers)."""
from unittest.mock import patch, AsyncMock

import pytest

from korug.services.enrichment import (
    is_cloudflare_ip,
    detect_technologies,
    _parse_nmap_xml,
    EnrichResult,
    EnrichmentService,
)


_RESOLVED = {"A": ["1.2.3.4"], "AAAA": [], "CNAME": None, "MX": [], "NS": []}


@pytest.mark.asyncio
async def test_enrich_one_skips_http_probe_in_passive_mode():
    """Passive monitoring (do_probe=False) must resolve DNS but never probe the host."""
    svc = EnrichmentService()
    with patch.object(svc, "_resolve", return_value=dict(_RESOLVED)), \
         patch.object(svc, "_probe", new=AsyncMock()) as probe:
        res = await svc._enrich_one(session=None, name="x.example.com", do_ports=False, do_probe=False)
    probe.assert_not_called()
    assert res.resolved_ips == ["1.2.3.4"]
    assert res.is_alive is False


@pytest.mark.asyncio
async def test_enrich_one_probes_in_active_mode():
    svc = EnrichmentService()
    with patch.object(svc, "_resolve", return_value=dict(_RESOLVED)), \
         patch.object(svc, "_probe", new=AsyncMock()) as probe:
        await svc._enrich_one(session=None, name="x.example.com", do_ports=False, do_probe=True)
    probe.assert_called_once()


NMAP_XML = """<?xml version="1.0"?>
<nmaprun>
  <host>
    <ports>
      <port protocol="tcp" portid="22">
        <state state="open"/>
        <service name="ssh" product="OpenSSH" version="8.9"/>
      </port>
      <port protocol="tcp" portid="80">
        <state state="closed"/>
        <service name="http"/>
      </port>
      <port protocol="tcp" portid="443">
        <state state="open"/>
        <service name="https" product="nginx" version="1.25.3"/>
      </port>
    </ports>
  </host>
</nmaprun>"""


def test_parse_nmap_xml_extracts_open_ports_with_service():
    ports = _parse_nmap_xml(NMAP_XML)
    assert [p["port"] for p in ports] == [22, 443]  # 80 is closed -> excluded
    ssh = next(p for p in ports if p["port"] == 22)
    assert ssh["service"] == "ssh" and ssh["product"] == "OpenSSH" and ssh["version"] == "8.9"


def test_parse_nmap_xml_handles_garbage():
    assert _parse_nmap_xml("not xml") == []
    assert _parse_nmap_xml("") == []


def test_cloudflare_ip_detection():
    assert is_cloudflare_ip("104.16.1.1") is True      # 104.16.0.0/13
    assert is_cloudflare_ip("172.64.1.1") is True       # 172.64.0.0/13
    assert is_cloudflare_ip("8.8.8.8") is False
    assert is_cloudflare_ip("not-an-ip") is False


def test_detect_technologies_from_headers_and_body():
    tech = detect_technologies(
        {"Server": "nginx/1.25", "X-Powered-By": "PHP/8.2"},
        '<html><meta name="generator" content="WordPress 6.5"><div class="wp-content"></div></html>',
    )
    assert "nginx" in tech
    assert "PHP" in tech
    assert "WordPress" in tech


def test_detect_technologies_cloudflare_header():
    tech = detect_technologies({"CF-RAY": "abc", "Server": "cloudflare"}, "")
    assert "Cloudflare" in tech


def test_enrich_result_resolved():
    r = EnrichResult()
    assert r.resolved() is False
    r.dns_records["A"] = ["1.2.3.4"]
    assert r.resolved() is True


def test_port_list_parsed_from_config():
    svc = EnrichmentService()
    assert 443 in svc.ports and 80 in svc.ports
    assert all(isinstance(p, int) for p in svc.ports)


@pytest.mark.asyncio
async def test_enrich_skips_unresolved(monkeypatch):
    """A name that doesn't resolve is returned but not probed."""
    svc = EnrichmentService()
    monkeypatch.setattr(svc, "_resolve",
                        lambda name: {"A": [], "AAAA": [], "CNAME": None, "MX": [], "NS": []})

    async def fail_probe(*a, **k):
        raise AssertionError("probe should not run for unresolved names")
    monkeypatch.setattr(svc, "_probe", fail_probe)

    results = await svc.enrich(["dead.example.com"])
    assert results["dead.example.com"].is_alive is False
    assert results["dead.example.com"].resolved() is False
