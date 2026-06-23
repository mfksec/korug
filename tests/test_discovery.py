"""Tests for the passive subdomain discovery service."""
import subprocess
from unittest.mock import patch, AsyncMock

import pytest

from korug.services.discovery import DiscoveryService, _clean


@pytest.fixture
def svc():
    return DiscoveryService()


# ---- name cleaning -------------------------------------------------------

def test_clean_accepts_subdomain_and_apex():
    assert _clean("www.example.com", "example.com") == "www.example.com"
    assert _clean("EXAMPLE.com", "example.com") == "example.com"


def test_clean_strips_wildcard_and_trailing_dot():
    assert _clean("*.example.com.", "example.com") == "example.com"


def test_clean_rejects_foreign_and_invalid():
    assert _clean("other.com", "example.com") is None
    assert _clean("notexample.com", "example.com") is None   # not a real subdomain
    assert _clean("foo@example.com", "example.com") is None
    assert _clean("", "example.com") is None


# ---- subfinder error handling (sync helper) ------------------------------

def test_subfinder_timeout_returns_empty(svc):
    with patch("subprocess.run", side_effect=subprocess.TimeoutExpired("subfinder", 60)):
        assert svc._run_subfinder("example.com") == set()


def test_subfinder_not_found_returns_empty(svc):
    with patch("subprocess.run", side_effect=FileNotFoundError()):
        assert svc._run_subfinder("example.com") == set()


# ---- discover() aggregation + source attribution -------------------------

@pytest.mark.asyncio
async def test_discover_merges_sources_and_attributes(svc):
    with patch.object(svc, "_crtsh", AsyncMock(return_value={"www.example.com", "*.example.com"})), \
         patch.object(svc, "_hackertarget", AsyncMock(return_value={"www.example.com"})), \
         patch.object(svc, "_certspotter", AsyncMock(return_value={"api.example.com"})), \
         patch.object(svc, "_rapiddns", AsyncMock(return_value=set())), \
         patch.object(svc, "_alienvault", AsyncMock(return_value=set())), \
         patch.object(svc, "_threatminer", AsyncMock(return_value=set())), \
         patch.object(svc, "_wayback", AsyncMock(return_value={"other.com"})), \
         patch.object(svc, "_bufferover", AsyncMock(return_value=set())), \
         patch.object(svc, "_threatcrowd", AsyncMock(return_value=set())), \
         patch.object(svc, "_run_subfinder", return_value={"mail.example.com"}), \
         patch.object(svc, "_run_amass", return_value=set()):

        found = await svc.discover("example.com")

    # foreign domain dropped, wildcard normalised to apex, apex seeded
    assert "other.com" not in found
    assert found["www.example.com"] == {"crt.sh", "hackertarget"}
    assert "api.example.com" in found
    assert "mail.example.com" in found
    assert "example.com" in found  # seed + wildcard
    assert "seed" in found["example.com"]


@pytest.mark.asyncio
async def test_discover_survives_source_exception(svc):
    with patch.object(svc, "_crtsh", AsyncMock(side_effect=RuntimeError("boom"))), \
         patch.object(svc, "_hackertarget", AsyncMock(return_value={"ok.example.com"})), \
         patch.object(svc, "_certspotter", AsyncMock(return_value=set())), \
         patch.object(svc, "_rapiddns", AsyncMock(return_value=set())), \
         patch.object(svc, "_alienvault", AsyncMock(return_value=set())), \
         patch.object(svc, "_threatminer", AsyncMock(return_value=set())), \
         patch.object(svc, "_wayback", AsyncMock(return_value=set())), \
         patch.object(svc, "_bufferover", AsyncMock(return_value=set())), \
         patch.object(svc, "_threatcrowd", AsyncMock(return_value=set())), \
         patch.object(svc, "_run_subfinder", return_value=set()), \
         patch.object(svc, "_run_amass", return_value=set()):

        found = await svc.discover("example.com")

    # crt.sh blew up but the scan still produced results
    assert "ok.example.com" in found
