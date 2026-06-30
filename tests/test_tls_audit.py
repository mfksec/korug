"""Tests for the tlsx TLS-audit service (pure parsing/assessment helpers)."""
from korug.services.tls_audit import (
    assess, parse_jsonl, host_of, is_weak_cipher,
)


def test_host_of_normalizes():
    assert host_of("https://sub.example.com:443/x") == "sub.example.com"
    assert host_of("sub.example.com:443") == "sub.example.com"
    assert host_of("HTTPS://Sub.Example.com") == "sub.example.com"
    assert host_of("") is None
    assert host_of(None) is None


def test_is_weak_cipher():
    assert is_weak_cipher("TLS_RSA_WITH_RC4_128_SHA") is True
    assert is_weak_cipher("TLS_RSA_WITH_3DES_EDE_CBC_SHA") is True
    assert is_weak_cipher("TLS_RSA_WITH_NULL_SHA") is True
    assert is_weak_cipher("TLS_AES_256_GCM_SHA384") is False
    assert is_weak_cipher("TLS_ECDHE_RSA_WITH_AES_128_GCM_SHA256") is False
    assert is_weak_cipher("") is False
    assert is_weak_cipher(None) is False


def test_assess_clean_cert_has_no_findings():
    rec = {
        "host": "good.example.com", "tls_version": "tls13",
        "cipher": "TLS_AES_256_GCM_SHA384", "expired": False,
        "self_signed": False, "mismatched": False, "untrusted": False,
    }
    assert assess(rec) == []


def test_assess_flags_cert_trust_problems():
    rec = {"host": "h", "expired": True, "self_signed": True, "mismatched": True}
    issues = {f["issue"] for f in assess(rec)}
    assert {"expired-cert", "self-signed-cert", "hostname-mismatch"} <= issues


def test_assess_flags_deprecated_tls_version():
    findings = assess({"host": "h", "tls_version": "TLS 1.0"})
    assert any(f["issue"] == "tls10" for f in findings)
    findings = assess({"host": "h", "tls_version": "SSLv3"})
    assert any(f["issue"] == "sslv3" for f in findings)


def test_assess_flags_weak_cipher():
    findings = assess({"host": "h", "cipher": "TLS_RSA_WITH_RC4_128_MD5"})
    assert any(f["issue"] == "weak-cipher" for f in findings)


def test_assess_expiring_soon_within_window_only():
    assert any(f["issue"] == "expiring-soon" for f in assess({"host": "h", "not_after_days": 5}))
    assert not any(f["issue"] == "expiring-soon" for f in assess({"host": "h", "not_after_days": 90}))
    # Already-expired is reported via the `expired` boolean, not expiring-soon.
    assert not any(f["issue"] == "expiring-soon" for f in assess({"host": "h", "not_after_days": -3}))


def test_parse_jsonl_reads_field_aliases_and_skips_junk():
    out = "\n".join([
        '{"host":"a.example.com","port":443,"tls_version":"tls10","cipher":"x","self-signed":true}',
        '{"input":"b.example.com:443","version":"tls13","notAfter":"2030-01-01"}',
        "",
        "not-json",
        '{"port":443}',  # no host/input -> skipped
    ])
    recs = parse_jsonl(out)
    assert len(recs) == 2
    assert recs[0]["host"] == "a.example.com"
    assert recs[0]["self_signed"] is True
    assert recs[0]["tls_version"] == "tls10"
    assert recs[1]["host"] == "b.example.com"
    assert recs[1]["tls_version"] == "tls13"
    assert recs[1]["not_after"] == "2030-01-01"


def test_parse_jsonl_empty():
    assert parse_jsonl("") == []
    assert parse_jsonl(None) == []
