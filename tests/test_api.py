"""Basic tests for korug."""
import json
from datetime import datetime


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
    """Test getting results for a new domain before any scan runs."""
    # Create domain
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


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
