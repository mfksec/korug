"""Tests for the crt.sh certificate service."""
from datetime import datetime
from unittest.mock import patch

import pytest

from korug.services import certificates as certs
from korug.services.certificates import _parse_row, _parse_ts


# ---- pure parsing --------------------------------------------------------

def test_parse_ts_handles_known_formats_and_garbage():
    assert _parse_ts("2024-01-02T03:04:05") == datetime(2024, 1, 2, 3, 4, 5)
    assert _parse_ts("2024-01-02 03:04:05") == datetime(2024, 1, 2, 3, 4, 5)
    assert _parse_ts(None) is None
    assert _parse_ts("not-a-date") is None


def test_parse_row_extracts_fields_and_splits_sans():
    row = {
        "serial_number": "ABC123",
        "issuer_name": "C=US, O=Let's Encrypt, CN=R3",
        "common_name": "www.example.com",
        "name_value": "www.example.com\nexample.com\n*.example.com",
        "not_before": "2024-01-01T00:00:00",
        "not_after": "2024-04-01T00:00:00",
    }
    parsed = _parse_row(row)
    assert parsed["serial_number"] == "ABC123"
    assert parsed["common_name"] == "www.example.com"
    assert set(parsed["sans"]) == {"www.example.com", "example.com", "*.example.com"}
    assert parsed["not_before"] == datetime(2024, 1, 1)


# ---- fetch_certificates (mocked HTTP) ------------------------------------

class _FakeResp:
    def __init__(self, status, payload):
        self.status = status
        self._payload = payload

    async def __aenter__(self):
        return self

    async def __aexit__(self, *a):
        return False

    async def json(self, content_type=None):
        return self._payload


class _FakeSession:
    def __init__(self, resp):
        self._resp = resp

    async def __aenter__(self):
        return self

    async def __aexit__(self, *a):
        return False

    def get(self, url, params=None):
        return self._resp


@pytest.mark.asyncio
async def test_fetch_certificates_dedupes_by_serial():
    payload = [
        {"serial_number": "S1", "issuer_name": "CN=R3", "common_name": "a.example.com",
         "name_value": "a.example.com", "not_before": "2024-01-01T00:00:00", "not_after": "2024-04-01T00:00:00"},
        # same serial, older issuance -> should not replace
        {"serial_number": "S1", "issuer_name": "CN=R3", "common_name": "a.example.com",
         "name_value": "a.example.com", "not_before": "2023-01-01T00:00:00", "not_after": "2023-04-01T00:00:00"},
        {"serial_number": "S2", "issuer_name": "CN=R10", "common_name": "b.example.com",
         "name_value": "b.example.com", "not_before": "2024-02-01T00:00:00", "not_after": "2024-05-01T00:00:00"},
    ]
    certs._cache.clear()
    with patch.object(certs.aiohttp, "ClientSession", return_value=_FakeSession(_FakeResp(200, payload))):
        out = await certs.fetch_certificates("uniqhost-dedupe.example.com")
    serials = sorted(c["serial_number"] for c in out)
    assert serials == ["S1", "S2"]
    s1 = next(c for c in out if c["serial_number"] == "S1")
    assert s1["not_before"] == datetime(2024, 1, 1)  # newer issuance kept


@pytest.mark.asyncio
async def test_fetch_certificates_returns_empty_on_error_status():
    certs._cache.clear()
    with patch.object(certs.aiohttp, "ClientSession", return_value=_FakeSession(_FakeResp(503, None))):
        out = await certs.fetch_certificates("uniqhost-error.example.com")
    assert out == []
