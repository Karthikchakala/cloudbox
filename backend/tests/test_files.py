import io
import pytest

def test_file_upload_success(client, auth_headers):
    """Test authenticated file upload."""
    data = {
        "file": (io.BytesIO(b"Hello CloudBox Object Storage Content"), "test_document.txt")
    }
    res = client.post("/api/files", data=data, content_type="multipart/form-data", headers=auth_headers)
    assert res.status_code == 201
    res_data = res.get_json()
    assert "file" in res_data
    file_info = res_data["file"]
    assert file_info["original_filename"] == "test_document.txt"
    assert file_info["size_bytes"] == len(b"Hello CloudBox Object Storage Content")
    assert "checksum_sha256" in file_info
    assert len(file_info["checksum_sha256"]) == 64

def test_file_upload_unauthenticated(client):
    """Test file upload without authentication token (401)."""
    data = {
        "file": (io.BytesIO(b"Unauthorized data"), "unauth.txt")
    }
    res = client.post("/api/files", data=data, content_type="multipart/form-data")
    assert res.status_code == 401

def test_file_upload_empty_file(client, auth_headers):
    """Test uploading an empty 0-byte file (400)."""
    data = {
        "file": (io.BytesIO(b""), "empty.txt")
    }
    res = client.post("/api/files", data=data, content_type="multipart/form-data", headers=auth_headers)
    assert res.status_code == 400
    assert res.get_json()["code"] == "EMPTY_FILE"

def test_file_upload_missing_field(client, auth_headers):
    """Test request without 'file' field (400)."""
    res = client.post("/api/files", data={"wrong_field": "data"}, content_type="multipart/form-data", headers=auth_headers)
    assert res.status_code == 400
    assert res.get_json()["code"] == "MISSING_FILE_FIELD"

def test_file_listing_and_isolation(client, auth_headers, second_auth_headers):
    """Test that file listing only returns files belonging to the authenticated user."""
    # User 1 uploads file A
    client.post("/api/files", data={"file": (io.BytesIO(b"User 1 File A"), "file_a.txt")}, content_type="multipart/form-data", headers=auth_headers)
    # User 1 uploads file B
    client.post("/api/files", data={"file": (io.BytesIO(b"User 1 File B"), "file_b.txt")}, content_type="multipart/form-data", headers=auth_headers)
    # User 2 uploads file C
    client.post("/api/files", data={"file": (io.BytesIO(b"User 2 File C"), "file_c.txt")}, content_type="multipart/form-data", headers=second_auth_headers)

    # User 1 lists files
    res1 = client.get("/api/files", headers=auth_headers)
    assert res1.status_code == 200
    data1 = res1.get_json()
    assert len(data1["files"]) == 2
    filenames_1 = [f["original_filename"] for f in data1["files"]]
    assert "file_a.txt" in filenames_1
    assert "file_b.txt" in filenames_1
    assert "file_c.txt" not in filenames_1

    # User 2 lists files
    res2 = client.get("/api/files", headers=second_auth_headers)
    assert res2.status_code == 200
    data2 = res2.get_json()
    assert len(data2["files"]) == 1
    assert data2["files"][0]["original_filename"] == "file_c.txt"

def test_file_download_and_cross_user_protection(client, auth_headers, second_auth_headers):
    """Test file download and verify User 2 cannot access or download User 1's file."""
    # User 1 uploads a file
    upload_res = client.post(
        "/api/files",
        data={"file": (io.BytesIO(b"Secret Document from User 1"), "secret.txt")},
        content_type="multipart/form-data",
        headers=auth_headers
    )
    file_id = upload_res.get_json()["file"]["id"]

    # User 1 downloads successfully
    dl_res = client.get(f"/api/files/{file_id}/download", headers=auth_headers)
    assert dl_res.status_code == 200
    assert dl_res.data == b"Secret Document from User 1"
    assert 'attachment; filename="secret.txt"' in dl_res.headers.get("Content-Disposition", "")

    # User 2 attempts to download User 1's file -> 404
    cross_dl_res = client.get(f"/api/files/{file_id}/download", headers=second_auth_headers)
    assert cross_dl_res.status_code == 404

    # User 2 attempts to get User 1's metadata -> 404
    cross_meta_res = client.get(f"/api/files/{file_id}", headers=second_auth_headers)
    assert cross_meta_res.status_code == 404

def test_file_deletion_and_cross_user_protection(client, auth_headers, second_auth_headers):
    """Test file deletion and verify User 2 cannot delete User 1's file."""
    # User 1 uploads file
    upload_res = client.post(
        "/api/files",
        data={"file": (io.BytesIO(b"Delete me soon"), "to_delete.txt")},
        content_type="multipart/form-data",
        headers=auth_headers
    )
    file_id = upload_res.get_json()["file"]["id"]

    # User 2 tries to delete User 1's file -> 404
    unauth_del = client.delete(f"/api/files/{file_id}", headers=second_auth_headers)
    assert unauth_del.status_code == 404

    # User 1 deletes the file -> 200
    del_res = client.delete(f"/api/files/{file_id}", headers=auth_headers)
    assert del_res.status_code == 200

    # Verify file is gone
    get_res = client.get(f"/api/files/{file_id}", headers=auth_headers)
    assert get_res.status_code == 404
