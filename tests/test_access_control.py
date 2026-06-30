"""Tests for the access-control + data-integrity fixes:

- domain-name validation
- XLSX export (regression: it 500'd for every domain)
- domain delete cascades to child rows (regression: FK violation 500)
- RBAC: viewers are read-only (write endpoints require admin)
"""
from datetime import datetime

from fastapi.testclient import TestClient

from korug.db import get_db
from korug.main import app
from korug.auth_utils import create_access_token
from korug.models import Domain, Alert, Subdomain, Vulnerability


def _client_as(db_session, username):
    app.dependency_overrides[get_db] = lambda: db_session
    c = TestClient(app)
    c.headers.update({"Authorization": f"Bearer {create_access_token({'sub': username, 'type': 'access'})}"})
    return c


# ---------------- Domain-name validation ----------------

def test_invalid_domain_names_are_rejected(client):
    # (A pasted URL is leniently normalized — scheme/path stripped — so it's
    # tested separately in test_valid_domain_is_normalized, not here.)
    for bad in ["not a domain", "a b c", "javascript:alert(1)", "192.168.0.0/16", "localhost", "-bad.com"]:
        r = client.post("/api/domains/", json={"domain_name": bad})
        assert r.status_code == 422, f"expected 422 for {bad!r}, got {r.status_code}"


def test_valid_domain_is_normalized(client):
    r = client.post("/api/domains/", json={"domain_name": "HTTPS://Example.COM/some/path"})
    assert r.status_code == 201
    assert r.json()["domain_name"] == "example.com"  # scheme/path stripped, lowercased


def test_ip_addresses_are_not_valid_domains(client):
    assert client.post("/api/domains/", json={"domain_name": "10.0.0.1"}).status_code == 422


# ---------------- XLSX export (regression) ----------------

def test_export_xlsx_succeeds_even_with_no_scan_data(client, db_session):
    d = Domain(domain_name="empty-export.com", monitor_mode="active")
    db_session.add(d)
    db_session.commit()
    db_session.refresh(d)

    r = client.get(f"/api/export/xlsx/{d.id}")
    assert r.status_code == 200
    assert "spreadsheetml" in r.headers["content-type"]
    assert len(r.content) > 0  # a real (if mostly-empty) workbook


def test_export_xlsx_404_for_missing_domain(client):
    assert client.get("/api/export/xlsx/999999").status_code == 404


# ---------------- Domain delete cascade (regression) ----------------

def test_delete_domain_cascades_children(client, db_session):
    d = Domain(domain_name="cascade-me.com", monitor_mode="active")
    db_session.add(d)
    db_session.commit()
    db_session.refresh(d)
    sub = Subdomain(domain_id=d.id, subdomain="api.cascade-me.com")
    db_session.add(sub)
    db_session.commit()
    db_session.refresh(sub)
    db_session.add(Vulnerability(subdomain_id=sub.id, domain_id=d.id, vuln_type="dns_orphan", confidence_score=50.0))
    db_session.add(Alert(domain_id=d.id, target="api.cascade-me.com", alert_type="dns_orphan",
                         severity="medium", message="x", created_at=datetime.utcnow()))
    db_session.commit()
    did = d.id  # capture before delete — the ORM instance is invalidated afterward

    # Previously a 500 (FK violation on alerts/subdomains); now a clean cascade.
    r = client.delete(f"/api/domains/{did}")
    assert r.status_code == 204
    assert db_session.query(Domain).filter(Domain.id == did).first() is None
    assert db_session.query(Alert).filter(Alert.domain_id == did).count() == 0
    assert db_session.query(Subdomain).filter(Subdomain.domain_id == did).count() == 0
    assert db_session.query(Vulnerability).filter(Vulnerability.domain_id == did).count() == 0


# ---------------- RBAC: viewers are read-only ----------------

def test_viewer_cannot_create_or_delete_domains(client, db_session, test_user_viewer):
    vc = _client_as(db_session, "vieweruser")
    assert vc.post("/api/domains/", json={"domain_name": "viewer-add.com"}).status_code == 403
    assert vc.delete("/api/domains/1").status_code == 403
    assert vc.put("/api/domains/1", json={"enabled": False}).status_code == 403


def test_viewer_cannot_trigger_or_cancel_scans(client, db_session, test_user_viewer):
    vc = _client_as(db_session, "vieweruser")
    assert vc.post("/api/scans/1/scan").status_code == 403
    assert vc.post("/api/scans/1/scan/cancel").status_code == 403


def test_viewer_cannot_mutate_findings_or_alerts(client, db_session, test_user_viewer):
    vc = _client_as(db_session, "vieweruser")
    assert vc.patch("/api/vulnerabilities/1", json={"is_false_positive": True}).status_code == 403
    assert vc.post("/api/alerts/1/resolve").status_code == 403
    assert vc.delete("/api/alerts/1").status_code == 403


def test_viewer_can_still_read(client, db_session, test_user_viewer):
    vc = _client_as(db_session, "vieweruser")
    assert vc.get("/api/domains/").status_code == 200
    assert vc.get("/api/vulnerabilities/").status_code == 200
    assert vc.get("/api/scans/assets").status_code == 200


def test_admin_can_create_and_delete_domains(client):
    r = client.post("/api/domains/", json={"domain_name": "admin-can.com"})
    assert r.status_code == 201
    did = r.json()["id"]
    assert client.delete(f"/api/domains/{did}").status_code == 204
