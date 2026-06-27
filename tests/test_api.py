"""Basic tests for korug."""
import json
from datetime import datetime

import pytest


def test_health_check(client):
    """Test health check endpoint."""
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "healthy"


def test_logout(client):
    """Test logout endpoint invalidates the token."""
    response = client.post("/api/auth/logout")
    assert response.status_code == 200
    assert response.json()["message"] == "Logged out successfully"


def test_revoked_token_returns_401(client):
    """Test that a token used after logout is rejected with 401."""
    # Logout to blacklist the current token
    logout_response = client.post("/api/auth/logout")
    assert logout_response.status_code == 200

    # Subsequent request with the same (now revoked) token should be rejected
    response = client.get("/api/auth/me")
    assert response.status_code == 401


def test_create_domain(client):
    """Test creating a domain."""
    response = client.post(
        "/api/domains/",
        json={"domain_name": "example.com"}
    )
    assert response.status_code == 201
    data = response.json()
    assert data["domain_name"] == "example.com"
    assert data["enabled"] is True
    assert data["id"] is not None


def test_list_domains(client):
    """Test listing domains."""
    # Create a domain first
    client.post("/api/domains/", json={"domain_name": "example.com"})
    client.post("/api/domains/", json={"domain_name": "test.com"})
    
    response = client.get("/api/domains/")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 2
    assert data[0]["domain_name"] in ["example.com", "test.com"]


def test_get_domain(client):
    """Test getting a specific domain."""
    # Create domain
    create_response = client.post(
        "/api/domains/",
        json={"domain_name": "example.com"}
    )
    domain_id = create_response.json()["id"]
    
    response = client.get(f"/api/domains/{domain_id}")
    assert response.status_code == 200
    data = response.json()
    assert data["domain_name"] == "example.com"
    assert data["id"] == domain_id


def test_update_domain(client):
    """Test updating a domain."""
    # Create domain
    create_response = client.post(
        "/api/domains/",
        json={"domain_name": "example.com"}
    )
    domain_id = create_response.json()["id"]
    
    response = client.put(
        f"/api/domains/{domain_id}",
        json={"enabled": False}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["enabled"] is False


def test_delete_domain(client):
    """Test deleting a domain."""
    # Create domain
    create_response = client.post(
        "/api/domains/",
        json={"domain_name": "example.com"}
    )
    domain_id = create_response.json()["id"]
    
    response = client.delete(f"/api/domains/{domain_id}")
    assert response.status_code == 204
    
    # Verify it's deleted
    get_response = client.get(f"/api/domains/{domain_id}")
    assert get_response.status_code == 404


def test_duplicate_domain(client):
    """Test creating duplicate domain fails."""
    client.post("/api/domains/", json={"domain_name": "example.com"})
    
    response = client.post(
        "/api/domains/",
        json={"domain_name": "example.com"}
    )
    assert response.status_code == 409


def test_list_vulnerabilities_empty(client):
    """Test listing vulnerabilities when none exist."""
    response = client.get("/api/vulnerabilities/")
    assert response.status_code == 200
    assert response.json() == []


def test_get_nonexistent_domain(client):
    """Test getting a domain that doesn't exist."""
    response = client.get("/api/domains/999")
    assert response.status_code == 404


def test_get_scan_results_empty(client):
    """A freshly created domain has no results yet.

    Auto-discovery is disabled in tests (ENABLE_AUTO_DISCOVERY=false) so domain
    creation performs no network I/O; results are empty until a scan runs.
    """
    create_response = client.post(
        "/api/domains/",
        json={"domain_name": "example.com"}
    )
    domain_id = create_response.json()["id"]

    response = client.get(f"/api/scans/{domain_id}/results")
    assert response.status_code == 200
    data = response.json()
    assert data["domain"]["id"] == domain_id
    assert isinstance(data["subdomains"], list)
    assert data["subdomains"] == []
    assert data["vulnerabilities"] == []


def _seed_subdomain(db, *, gone=False):
    """Insert a domain + subdomain (with a finding, cert and change) for detail tests."""
    from korug.models import Domain, Subdomain, Vulnerability, Certificate, AssetChange

    domain = Domain(domain_name="example.com")
    db.add(domain)
    db.commit()
    db.refresh(domain)

    sub = Subdomain(domain_id=domain.id, subdomain="www.example.com", is_alive=True, is_gone=gone)
    db.add(sub)
    db.commit()
    db.refresh(sub)

    db.add(Vulnerability(subdomain_id=sub.id, domain_id=domain.id, vuln_type="cname_orphan", confidence_score=85.0,
                         details=json.dumps({"message": "dangling CNAME"})))
    db.add(Certificate(subdomain_id=sub.id, domain_id=domain.id, issuer="CN=R3", common_name="www.example.com",
                       sans=json.dumps(["www.example.com"]), serial_number="S1"))
    db.add(AssetChange(domain_id=domain.id, subdomain_id=sub.id, change_type="subdomain_added",
                       target=sub.subdomain, new_value="1.2.3.4"))
    db.commit()
    return domain, sub


def test_get_subdomain_detail(client, db_session):
    """Subdomain detail returns the asset plus its vulns, certs and changes."""
    _, sub = _seed_subdomain(db_session)

    response = client.get(f"/api/scans/subdomain/{sub.id}")
    assert response.status_code == 200
    data = response.json()
    assert data["asset"]["subdomain"] == "www.example.com"
    assert data["asset"]["domain_name"] == "example.com"
    assert len(data["vulnerabilities"]) == 1
    assert data["vulnerabilities"][0]["vuln_type"] == "cname_orphan"
    assert len(data["certificates"]) == 1
    assert data["certificates"][0]["serial_number"] == "S1"
    assert any(c["change_type"] == "subdomain_added" for c in data["changes"])


def test_get_subdomain_detail_404(client):
    assert client.get("/api/scans/subdomain/99999").status_code == 404


def test_list_assets_includes_gone_flag_and_sorts(client, db_session):
    """Assets list exposes is_gone and honours the sort/dir params."""
    _seed_subdomain(db_session, gone=True)

    response = client.get("/api/scans/assets", params={"sort": "subdomain", "dir": "desc"})
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 1
    assert data["assets"][0]["is_gone"] is True


def test_list_assets_gone_filter(client, db_session):
    _seed_subdomain(db_session, gone=True)
    # Only gone assets
    gone = client.get("/api/scans/assets", params={"gone": True}).json()
    assert gone["count"] == 1
    # No live assets
    alive = client.get("/api/scans/assets", params={"gone": False}).json()
    assert alive["count"] == 0


def test_list_changes(client, db_session):
    """The changes feed returns recorded asset changes with the domain name joined."""
    _seed_subdomain(db_session)

    response = client.get("/api/changes/")
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 1
    change = data["changes"][0]
    assert change["change_type"] == "subdomain_added"
    assert change["domain_name"] == "example.com"
    assert change["target"] == "www.example.com"


def test_list_changes_type_filter(client, db_session):
    _seed_subdomain(db_session)
    hit = client.get("/api/changes/", params={"change_type": "subdomain_added"}).json()
    assert hit["count"] == 1
    miss = client.get("/api/changes/", params={"change_type": "went_offline"}).json()
    assert miss["count"] == 0


@pytest.mark.asyncio
async def test_incremental_enrichment_isolates_failures(db_session, monkeypatch):
    """A rate-limit/error during CVE or cert lookup must not break the scan.

    The incremental enrichment helper isolates each host: a raising CVE/cert
    lookup is logged and skipped, the call returns normally, and the scan and
    its already-persisted subdomains remain intact.
    """
    from types import SimpleNamespace
    from korug.api import scans
    from korug.models import Domain, Subdomain, ScanHistory

    domain = Domain(domain_name="example.com")
    db_session.add(domain)
    db_session.commit()
    db_session.refresh(domain)
    sub = Subdomain(domain_id=domain.id, subdomain="www.example.com", is_alive=True)
    db_session.add(sub)
    scan = ScanHistory(domain_id=domain.id, status="running")
    db_session.add(scan)
    db_session.commit()
    db_session.refresh(sub)
    db_session.refresh(scan)

    # Force both enrichment steps on, then make them blow up as a rate-limit would.
    monkeypatch.setattr(
        "korug.config.get_settings",
        lambda: SimpleNamespace(enable_auto_cve=True, enable_cert_monitoring=True, nvd_api_key=""),
    )

    async def boom(*args, **kwargs):
        raise RuntimeError("429 rate limited")

    monkeypatch.setattr(scans, "_scan_cves", boom)
    monkeypatch.setattr(scans, "_scan_certificates", boom)

    # Must not raise despite both steps failing.
    result = await scans._run_incremental_enrichment(db_session, scan, [sub.id], {sub.subdomain: None})
    assert result == 0

    # Scan is untouched (still running, not failed) and the subdomain survives.
    db_session.refresh(scan)
    assert scan.status == "running"
    assert db_session.query(Subdomain).count() == 1


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
