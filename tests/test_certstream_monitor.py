"""Tests for the certstream live-CT monitor (pure helpers)."""
from korug.services.certstream_monitor import extract_domains, match_monitored


def test_extract_domains_from_certificate_update():
    msg = {
        "message_type": "certificate_update",
        "data": {"leaf_cert": {"all_domains": ["*.example.com", "example.com", "api.example.com"]}},
    }
    assert extract_domains(msg) == ["*.example.com", "example.com", "api.example.com"]


def test_extract_domains_ignores_other_message_types():
    assert extract_domains({"message_type": "heartbeat"}) == []
    assert extract_domains({}) == []


def test_match_monitored_matches_apex_and_subdomains():
    apexes = {"example.com": 1, "other.org": 2}
    matches = match_monitored(["*.example.com", "api.example.com", "example.com", "nope.test"], apexes)
    # wildcard normalizes to apex; subdomain + apex match; foreign domain ignored
    assert matches == {"example.com": 1, "api.example.com": 1}


def test_match_monitored_prefers_most_specific_apex():
    # Both apexes monitored; a host under the deeper apex maps to it, not the parent.
    apexes = {"example.com": 1, "corp.example.com": 2}
    matches = match_monitored(["host.corp.example.com"], apexes)
    assert matches == {"host.corp.example.com": 2}


def test_match_monitored_no_apexes():
    assert match_monitored(["api.example.com"], {}) == {}
