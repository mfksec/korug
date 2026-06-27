"""Tests for fingerprint-based subdomain-takeover detection."""
import json
from unittest.mock import patch

import pytest

from korug.services.takeover_fingerprints import (
    match_cname,
    body_indicates_takeover,
)
from korug.services.takeover_detection import TakeoverDetector


@pytest.fixture
def detector():
    return TakeoverDetector()


# ---- fingerprint matchers (pure) -----------------------------------------

def test_match_cname_identifies_service():
    matches = match_cname("myorg.github.io")
    assert any(m["service"] == "GitHub Pages" for m in matches)


def test_match_cname_is_case_insensitive_and_trims_dot():
    assert match_cname("MyApp.HerokuApp.com.")[0]["service"] == "Heroku"


def test_match_cname_returns_empty_for_unknown_target():
    assert match_cname("internal.corp.example.com") == []
    assert match_cname(None) == []


def test_body_indicates_takeover():
    entry = next(m for m in match_cname("x.github.io"))
    assert body_indicates_takeover(entry, "<h1>There isn't a GitHub Pages site here.</h1>")
    assert not body_indicates_takeover(entry, "<html>totally normal site</html>")
    assert not body_indicates_takeover(entry, "")


# ---- service takeover detection ------------------------------------------

@pytest.mark.asyncio
async def test_fingerprint_match_flags_takeover(detector):
    """CNAME to a known service + matching body fingerprint => critical takeover."""
    dns_records = {"A": ["1.2.3.4"], "AAAA": [], "CNAME": "victim.github.io", "MX": [], "NS": []}
    # CNAME resolves (not NXDOMAIN), so detection must come from the body.
    with patch.object(detector, "_is_unresolvable", return_value=False):
        findings = await detector._check_service_takeover(
            "victim.example.com", dns_records,
            http_body="There isn't a GitHub Pages site here.",
        )
    assert len(findings) == 1
    f = findings[0]
    assert f["vuln_type"] == "subdomain_takeover"
    assert f["confidence_score"] >= 90
    details = json.loads(f["details"])
    assert details["service"] == "GitHub Pages"
    assert details["fingerprint_matched"] is True


@pytest.mark.asyncio
async def test_nxdomain_on_known_service_flags_without_body(detector):
    """A dangling (NXDOMAIN) CNAME to a known service is a takeover even with no body."""
    dns_records = {"A": [], "AAAA": [], "CNAME": "gone.herokuapp.com", "MX": [], "NS": []}
    with patch.object(detector, "_is_unresolvable", return_value=True):
        findings = await detector._check_service_takeover("app.example.com", dns_records, http_body=None)
    assert len(findings) == 1
    details = json.loads(findings[0]["details"])
    assert details["nxdomain"] is True
    assert findings[0]["confidence_score"] >= 90  # NXDOMAIN on a known service is critical


@pytest.mark.asyncio
async def test_no_signal_no_finding(detector):
    """Known-service CNAME that resolves and lacks the fingerprint => no false positive."""
    dns_records = {"A": ["1.2.3.4"], "AAAA": [], "CNAME": "live.github.io", "MX": [], "NS": []}
    with patch.object(detector, "_is_unresolvable", return_value=False):
        findings = await detector._check_service_takeover(
            "live.example.com", dns_records, http_body="<html>a perfectly normal published site</html>",
        )
    assert findings == []


@pytest.mark.asyncio
async def test_unknown_cname_is_not_a_service_finding(detector):
    dns_records = {"A": [], "AAAA": [], "CNAME": "thing.internal.example.com", "MX": [], "NS": []}
    findings = await detector._check_service_takeover("x.example.com", dns_records, http_body="anything")
    assert findings == []


@pytest.mark.asyncio
async def test_service_finding_suppresses_generic_cname_orphan(detector):
    """When the precise service check fires, the generic cname_orphan must not double-report."""
    dns_records = {"A": [], "AAAA": [], "CNAME": "gone.github.io", "MX": [], "NS": []}
    with patch.object(detector, "_is_unresolvable", return_value=True):
        findings = await detector.check_takeover_risks(
            "victim.example.com", dns_records, http_body=None,
        )
    types = [f["vuln_type"] for f in findings]
    assert "subdomain_takeover" in types
    assert "cname_orphan" not in types
