import pytest

def test_security_headers_present(client):
    """Test that all API responses contain mandatory security headers."""
    res = client.get("/health")
    assert res.status_code == 200
    assert "X-Request-ID" in res.headers
    assert res.headers.get("X-Content-Type-Options") == "nosniff"
    assert res.headers.get("X-Frame-Options") == "DENY"
    assert res.headers.get("Referrer-Policy") == "strict-origin-when-cross-origin"

def test_custom_request_id_propagation(client):
    """Test that client-supplied X-Request-ID is preserved and echoed."""
    custom_id = "trace-uuid-123456789"
    res = client.get("/health", headers={"X-Request-ID": custom_id})
    assert res.status_code == 200
    assert res.headers.get("X-Request-ID") == custom_id

def test_root_status_version(client):
    """Test root endpoint reports phase 5 status and enabled features."""
    res = client.get("/")
    assert res.status_code == 200
    data = res.get_json()
    assert data["version"] == "5.0.0-phase5"
    assert data["features"]["analytics"] is True
    assert data["features"]["production_hardened"] is True
    assert data["features"]["chunked_uploads"] is True
    assert data["features"]["background_processing"] is True
