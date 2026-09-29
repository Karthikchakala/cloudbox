import pytest
from app.config import Config
from app.services.audit_logger import sanitize_audit_data, log_security_event

def test_sanitize_audit_data_redacts_sensitive_keys():
    """Verify that passwords, tokens, and secret keys are automatically redacted."""
    raw_payload = {
        "username": "alice",
        "password": "SuperSecretPassword123!",
        "token": "jwt.header.payload.signature",
        "nested": {
            "api_key": "12345",
            "secret": "my-minio-secret",
            "email": "alice@cloudbox.local"
        }
    }

    sanitized = sanitize_audit_data(raw_payload)
    assert sanitized["username"] == "alice"
    assert sanitized["password"] == "[REDACTED]"
    assert sanitized["token"] == "[REDACTED]"
    assert sanitized["nested"]["secret"] == "[REDACTED]"
    assert sanitized["nested"]["email"] == "alice@cloudbox.local"

def test_log_security_event_structure(app):
    """Verify structured event generation with context."""
    with app.app_context():
        event = log_security_event(
            event_type="AUTH",
            action="LOGIN_TEST",
            status="SUCCESS",
            user_id="user-123",
            target_resource_id="res-456",
            details={"ip": "127.0.0.1", "password": "hidden_password"}
        )

        assert event["audit_type"] == "SECURITY_EVENT"
        assert event["event_type"] == "AUTH"
        assert event["action"] == "LOGIN_TEST"
        assert event["status"] == "SUCCESS"
        assert event["actor_user_id"] == "user-123"
        assert event["target_resource_id"] == "res-456"
        assert event["details"]["password"] == "[REDACTED]"

def test_production_config_rejects_weak_secrets():
    """Verify that default dev credentials trigger RuntimeError in production mode."""
    test_config = Config()
    test_config.APP_ENV = "production"
    test_config.SECRET_KEY = "cloudbox-dev-secret-key-phase2-active"

    with pytest.raises(RuntimeError) as excinfo:
        test_config.validate_production_secrets()

    assert "CRITICAL SECURITY CONFIGURATION ERROR" in str(excinfo.value)

def test_user_isolation_authorization(client, auth_headers, second_auth_headers):
    """Verify that User 2 cannot access, download, or delete User 1's files."""
    # User 1 uploads a file
    import io
    data = {"file": (io.BytesIO(b"Private user 1 content"), "private1.txt")}
    upload_res = client.post(
        "/api/files",
        headers=auth_headers,
        data=data,
        content_type="multipart/form-data"
    )
    assert upload_res.status_code == 201
    file_id = upload_res.get_json()["file"]["id"]

    # User 2 attempts to get metadata -> 404
    meta_res = client.get(f"/api/files/{file_id}", headers=second_auth_headers)
    assert meta_res.status_code == 404

    # User 2 attempts to download -> 404
    dl_res = client.get(f"/api/files/{file_id}/download", headers=second_auth_headers)
    assert dl_res.status_code == 404

    # User 2 attempts to delete -> 404
    del_res = client.delete(f"/api/files/{file_id}", headers=second_auth_headers)
    assert del_res.status_code == 404

def test_path_traversal_sanitization(client, auth_headers):
    """Verify that filenames with path traversal characters (../) are sanitized by secure_filename."""
    import io
    traversal_name = "../../../../etc/passwd"
    data = {"file": (io.BytesIO(b"root:x:0:0:root"), traversal_name)}
    upload_res = client.post(
        "/api/files",
        headers=auth_headers,
        data=data,
        content_type="multipart/form-data"
    )
    assert upload_res.status_code == 201
    saved_filename = upload_res.get_json()["file"]["original_filename"]
    assert ".." not in saved_filename
    assert "/" not in saved_filename
    assert "\\" not in saved_filename
    assert saved_filename in ("etc_passwd", "passwd")
