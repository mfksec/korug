"""Tests for the enrichment service (pure, deterministic helpers)."""
import pytest

from korug.services.enrichment import (
    is_cloudflare_ip,
    detect_technologies,
    EnrichResult,
    EnrichmentService,
)


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
