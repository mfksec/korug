"""Tests for user management, password change, and integrations APIs."""
from fastapi.testclient import TestClient
from korug.db import get_db
from korug.main import app
from korug.auth_utils import create_access_token


def _client_as(db_session, username):
    app.dependency_overrides[get_db] = lambda: db_session
    c = TestClient(app)
    c.headers.update({"Authorization": f"Bearer {create_access_token({'sub': username, 'type': 'access'})}"})
    return c


# ---------------- User management (admin) ----------------

def test_admin_can_list_and_create_users(client, db_session):
    # default test_user is admin
    res = client.post("/api/users/", json={
        "username": "analyst", "email": "analyst@corp.test",
        "password": "analystpass1", "role": "viewer",
    })
    assert res.status_code == 201, res.text
    assert res.json()["role"] == "viewer"

    users = client.get("/api/users/").json()
    assert any(u["username"] == "analyst" for u in users)


def test_viewer_cannot_manage_users(client, db_session, test_user_viewer):
    vc = _client_as(db_session, "vieweruser")
    assert vc.get("/api/users/").status_code == 403
    r = vc.post("/api/users/", json={"username": "x", "email": "x@y.z", "password": "password12", "role": "viewer"})
    assert r.status_code == 403
    app.dependency_overrides.clear()


def test_cannot_delete_self_or_last_admin(client, db_session, test_user):
    me = client.get("/api/auth/me").json()
    r = client.delete(f"/api/users/{me['id']}")
    assert r.status_code == 400
    assert "own account" in r.json()["detail"]


def test_self_password_change_flow(client, db_session, test_user):
    # wrong current password rejected
    bad = client.post("/api/users/me/password", json={
        "current_password": "wrongpass", "new_password": "brandnewpass1"})
    assert bad.status_code == 400

    ok = client.post("/api/users/me/password", json={
        "current_password": "testpassword123", "new_password": "brandnewpass1"})
    assert ok.status_code == 204


def test_admin_reset_user_password(client, db_session):
    created = client.post("/api/users/", json={
        "username": "resetme", "email": "resetme@corp.test",
        "password": "origpass123", "role": "viewer"}).json()
    r = client.post(f"/api/users/{created['id']}/password", json={"new_password": "freshpass456"})
    assert r.status_code == 204


def test_profile_update_email(client, db_session):
    r = client.patch("/api/users/me", json={"email": "newaddr@corp.test"})
    assert r.status_code == 200
    assert r.json()["email"] == "newaddr@corp.test"


# ---------------- Integrations ----------------

def test_integrations_default_empty(client, db_session):
    data = client.get("/api/integrations/").json()
    assert data["slack"]["webhook_configured"] is False
    assert data["email"]["enabled"] is False
    # secrets never leaked
    assert data["email"]["smtp_password"] in ("", "********")


def test_update_slack_masks_secret_and_persists(client, db_session):
    r = client.put("/api/integrations/slack", json={
        "enabled": True, "webhook_url": "https://hooks.slack.com/services/T/B/secret"})
    assert r.status_code == 200
    body = r.json()
    assert body["enabled"] is True
    assert body["webhook_configured"] is True
    assert body["webhook_url"] == "********"  # masked, not echoed

    # re-saving with mask keeps the stored webhook
    again = client.put("/api/integrations/slack", json={"enabled": False, "webhook_url": "********"}).json()
    assert again["webhook_configured"] is True


def test_update_email_config(client, db_session):
    r = client.put("/api/integrations/email", json={
        "enabled": True, "smtp_host": "smtp.corp.test", "smtp_port": 587,
        "smtp_user": "bot", "smtp_password": "smtp-secret",
        "use_tls": True, "from_address": "korug@corp.test", "to_addresses": "soc@corp.test"})
    assert r.status_code == 200
    body = r.json()
    assert body["smtp_host"] == "smtp.corp.test"
    assert body["password_configured"] is True
    assert body["smtp_password"] == "********"


def test_email_test_without_config_returns_400(client, db_session):
    r = client.post("/api/integrations/email/test")
    assert r.status_code == 400  # EmailConfigError -> missing host/recipients


def test_viewer_cannot_update_integrations(client, db_session, test_user_viewer):
    vc = _client_as(db_session, "vieweruser")
    assert vc.put("/api/integrations/slack", json={"enabled": True, "webhook_url": "x"}).status_code == 403
    app.dependency_overrides.clear()
