"""Tests for ownership attribution + active-scan scope gating."""
from korug.services.scope import classify
from korug.services.enrichment import ip_in_cidrs


APEXES = ["example.com"]


def test_ip_in_cidrs():
    assert ip_in_cidrs("10.0.0.5", ["10.0.0.0/24"]) is True
    assert ip_in_cidrs("10.0.1.5", ["10.0.0.0/24"]) is False
    assert ip_in_cidrs("not-an-ip", ["10.0.0.0/24"]) is False
    assert ip_in_cidrs("10.0.0.5", []) is False


def test_owned_name_and_ip_is_high_confidence_and_scannable():
    v = classify("api.example.com", ["10.0.0.5"], None,
                 owned_cidrs=["10.0.0.0/24"], monitored_apexes=APEXES)
    assert v["confidence"] == 100.0
    assert v["hosting"] == "first_party"
    assert v["host_active_allowed"] is True
    assert v["port_scan_allowed"] is True


def test_third_party_app_cname_blocks_host_active_scan():
    # blog.example.com -> someone.github.io: the NAME is ours but the APP is GitHub's.
    v = classify("blog.example.com", [], "myorg.github.io",
                 owned_cidrs=[], monitored_apexes=APEXES)
    assert v["third_party_app"] is True
    assert v["hosting"] == "third_party"
    assert v["host_active_allowed"] is False   # must not nuclei-scan a third party's app
    assert v["confidence"] < 100


def test_cdn_fronted_host_is_still_host_scannable_but_not_port_scannable():
    cf_ip = "104.16.0.1"  # within a Cloudflare range
    v = classify("www.example.com", [cf_ip], None,
                 owned_cidrs=[], monitored_apexes=APEXES)
    assert v["on_cdn"] is True
    assert v["hosting"] == "cdn"
    assert v["host_active_allowed"] is True     # your app behind a CDN — fine to nuclei
    assert v["port_scan_allowed"] is False      # never port-scan a shared CDN IP


def test_owned_cidrs_required_restricts_port_scan_to_owned_ips():
    # Non-CDN IP outside declared ranges → not port-scannable when ranges are declared.
    v = classify("host.example.com", ["8.8.8.8"], None,
                 owned_cidrs=["10.0.0.0/24"], monitored_apexes=APEXES)
    assert v["ip_owned"] is False
    assert v["port_scan_allowed"] is False
    # ...but with no ranges declared, any non-CDN IP is allowed (fallback).
    v2 = classify("host.example.com", ["8.8.8.8"], None,
                  owned_cidrs=[], monitored_apexes=APEXES)
    assert v2["port_scan_allowed"] is True


def test_unowned_name_gets_low_confidence():
    v = classify("foreign.test", ["8.8.8.8"], None, owned_cidrs=[], monitored_apexes=APEXES)
    assert v["name_owned"] is False
    assert v["host_active_allowed"] is False
    assert v["confidence"] <= 10
