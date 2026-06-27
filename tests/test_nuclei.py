"""Tests for the nuclei service (pure parsing/mapping helpers)."""
from korug.services.nuclei import parse_jsonl, severity_confidence, host_of


def test_severity_confidence_mapping():
    assert severity_confidence("critical") == 95.0
    assert severity_confidence("HIGH") == 85.0
    assert severity_confidence("medium") == 65.0
    assert severity_confidence("low") == 45.0
    assert severity_confidence("info") == 20.0
    assert severity_confidence(None) == 30.0
    assert severity_confidence("weird") == 30.0


def test_host_of_normalizes_urls_ports_paths():
    assert host_of("https://sub.example.com/path") == "sub.example.com"
    assert host_of("sub.example.com:443") == "sub.example.com"
    assert host_of("HTTP://Sub.Example.com") == "sub.example.com"
    assert host_of("sub.example.com") == "sub.example.com"
    assert host_of("") is None
    assert host_of(None) is None


def test_parse_jsonl_extracts_findings():
    out = "\n".join([
        '{"template-id":"CVE-2021-44228","info":{"name":"Log4j RCE","severity":"critical","description":"jndi"},"host":"https://app.example.com","matched-at":"https://app.example.com/","type":"http"}',
        '{"template-id":"tech-detect","info":{"name":"Nginx","severity":"info"},"host":"app.example.com:443"}',
        "",
        "not-json",
        '{"info":{"name":"missing id"}}',  # no template-id -> skipped
    ])
    findings = parse_jsonl(out)
    assert len(findings) == 2
    f = findings[0]
    assert f["template_id"] == "CVE-2021-44228"
    assert f["severity"] == "critical"
    assert f["host"] == "app.example.com"
    assert findings[1]["template_id"] == "tech-detect"
    assert findings[1]["host"] == "app.example.com"


def test_parse_jsonl_empty():
    assert parse_jsonl("") == []
    assert parse_jsonl(None) == []
