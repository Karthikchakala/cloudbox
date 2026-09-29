import io
from datetime import datetime, timezone, timedelta

def test_create_and_access_public_share(client, auth_headers):
    """Test standard public share link creation and recipient download."""
    # Upload file
    res = client.post(
        "/api/files",
        data={"file": (io.BytesIO(b"Public Shared Knowledge Payload"), "public_note.txt")},
        content_type="multipart/form-data",
        headers=auth_headers
    )
    file_id = res.get_json()["file"]["id"]

    # Create share link
    share_res = client.post(
        f"/api/files/{file_id}/shares",
        json={"permission": "download"},
        headers=auth_headers
    )
    assert share_res.status_code == 201
    share_data = share_res.get_json()
    token = share_data["token"]
    assert "token_hash" not in share_data["share"]

    # Access without auth (as public recipient)
    info_res = client.get(f"/api/shared/{token}")
    assert info_res.status_code == 200
    info_data = info_res.get_json()
    assert info_data["original_filename"] == "public_note.txt"
    assert info_data["requires_password"] is False

    # Download without auth
    dl_res = client.get(f"/api/shared/{token}?download=true")
    assert dl_res.status_code == 200
    assert dl_res.data == b"Public Shared Knowledge Payload"

def test_share_link_expiration(client, auth_headers):
    """Test expired share link access rejection."""
    res = client.post(
        "/api/files",
        data={"file": (io.BytesIO(b"Expiring Data"), "expire.txt")},
        content_type="multipart/form-data",
        headers=auth_headers
    )
    file_id = res.get_json()["file"]["id"]

    # Create expired link in the past
    past_date = (datetime.now(timezone.utc) - timedelta(hours=1)).isoformat()
    share_res = client.post(
        f"/api/files/{file_id}/shares",
        json={"expires_at": past_date},
        headers=auth_headers
    )
    token = share_res.get_json()["token"]

    # Public recipient attempts to access -> 410 Gone
    access_res = client.get(f"/api/shared/{token}")
    assert access_res.status_code == 410

def test_share_link_revocation(client, auth_headers):
    """Test revoking a share link by owner."""
    res = client.post(
        "/api/files",
        data={"file": (io.BytesIO(b"Revocable Data"), "revoke.txt")},
        content_type="multipart/form-data",
        headers=auth_headers
    )
    file_id = res.get_json()["file"]["id"]

    share_res = client.post(f"/api/files/{file_id}/shares", json={}, headers=auth_headers)
    token = share_res.get_json()["token"]
    share_id = share_res.get_json()["share"]["id"]

    # Verify link works before revocation
    assert client.get(f"/api/shared/{token}").status_code == 200

    # Revoke link
    revoke_res = client.delete(f"/api/shares/{share_id}", headers=auth_headers)
    assert revoke_res.status_code == 200

    # Verify link is now rejected (410)
    assert client.get(f"/api/shared/{token}").status_code == 410

def test_password_protected_share(client, auth_headers):
    """Test password protected sharing link access control."""
    res = client.post(
        "/api/files",
        data={"file": (io.BytesIO(b"Secret Vault Content"), "classified.txt")},
        content_type="multipart/form-data",
        headers=auth_headers
    )
    file_id = res.get_json()["file"]["id"]

    # Create password-protected share
    share_res = client.post(
        f"/api/files/{file_id}/shares",
        json={"password": "ShareSecretPassword123!"},
        headers=auth_headers
    )
    token = share_res.get_json()["token"]

    # Access without password returns metadata indicating password is required
    meta_res = client.get(f"/api/shared/{token}")
    assert meta_res.status_code == 200
    assert meta_res.get_json()["requires_password"] is True

    # Verify password endpoint with incorrect password
    verify_bad = client.post(f"/api/shared/{token}/verify", json={"password": "WrongPassword"})
    assert verify_bad.status_code == 401

    # Verify password endpoint with correct password
    verify_good = client.post(f"/api/shared/{token}/verify", json={"password": "ShareSecretPassword123!"})
    assert verify_good.status_code == 200
    assert verify_good.get_json()["valid"] is True

    # Download with password header
    dl_good = client.get(f"/api/shared/{token}?download=true", headers={"X-Share-Password": "ShareSecretPassword123!"})
    assert dl_good.status_code == 200
    assert dl_good.data == b"Secret Vault Content"

def test_download_limit_enforcement(client, auth_headers):
    """Test max download limit enforcement."""
    res = client.post(
        "/api/files",
        data={"file": (io.BytesIO(b"Single Download Coupon"), "coupon.txt")},
        content_type="multipart/form-data",
        headers=auth_headers
    )
    file_id = res.get_json()["file"]["id"]

    # Create share link with max 1 download
    share_res = client.post(
        f"/api/files/{file_id}/shares",
        json={"max_downloads": 1},
        headers=auth_headers
    )
    token = share_res.get_json()["token"]

    # Download 1: Succeeds
    dl1 = client.get(f"/api/shared/{token}?download=true")
    assert dl1.status_code == 200

    # Download 2: Rejected (limit reached)
    dl2 = client.get(f"/api/shared/{token}?download=true")
    assert dl2.status_code == 410

def test_cannot_access_trashed_file_via_share(client, auth_headers):
    """Test that soft-deleting a file disables public sharing access immediately."""
    res = client.post(
        "/api/files",
        data={"file": (io.BytesIO(b"Ephemeral Shared Data"), "temp.txt")},
        content_type="multipart/form-data",
        headers=auth_headers
    )
    file_id = res.get_json()["file"]["id"]

    share_res = client.post(f"/api/files/{file_id}/shares", json={}, headers=auth_headers)
    token = share_res.get_json()["token"]

    # Move file to trash
    client.delete(f"/api/files/{file_id}", headers=auth_headers)

    # Public recipient cannot access trashed file -> 404
    assert client.get(f"/api/shared/{token}").status_code == 404
