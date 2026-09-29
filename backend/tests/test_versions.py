import io
import pytest

def test_initial_upload_creates_version_one(client, auth_headers):
    """Test that uploading a new file creates Version 1 automatically."""
    res = client.post(
        "/api/files",
        data={"file": (io.BytesIO(b"Version 1 Initial Content"), "doc.txt")},
        content_type="multipart/form-data",
        headers=auth_headers
    )
    assert res.status_code == 201
    file_id = res.get_json()["file"]["id"]

    # Check versions list
    ver_res = client.get(f"/api/files/{file_id}/versions", headers=auth_headers)
    assert ver_res.status_code == 200
    versions = ver_res.get_json()["versions"]
    assert len(versions) == 1
    assert versions[0]["version_number"] == 1
    assert versions[0]["is_current"] is True

def test_upload_new_version(client, auth_headers):
    """Test uploading Version 2 to an existing file."""
    # Upload v1
    res1 = client.post(
        "/api/files",
        data={"file": (io.BytesIO(b"Version 1 Data"), "doc.txt")},
        content_type="multipart/form-data",
        headers=auth_headers
    )
    file_id = res1.get_json()["file"]["id"]

    # Upload v2
    res2 = client.post(
        f"/api/files/{file_id}/versions",
        data={"file": (io.BytesIO(b"Version 2 Updated Data"), "doc.txt")},
        content_type="multipart/form-data",
        headers=auth_headers
    )
    assert res2.status_code == 201
    v2_data = res2.get_json()["version"]
    assert v2_data["version_number"] == 2
    assert v2_data["is_current"] is True

    # List versions
    ver_res = client.get(f"/api/files/{file_id}/versions", headers=auth_headers)
    versions = ver_res.get_json()["versions"]
    assert len(versions) == 2
    assert versions[0]["version_number"] == 2
    assert versions[0]["is_current"] is True
    assert versions[1]["version_number"] == 1
    assert versions[1]["is_current"] is False

def test_download_historical_version(client, auth_headers):
    """Test downloading historical version contents specifically."""
    res1 = client.post(
        "/api/files",
        data={"file": (io.BytesIO(b"First Version Content"), "history.txt")},
        content_type="multipart/form-data",
        headers=auth_headers
    )
    file_id = res1.get_json()["file"]["id"]

    # Upload v2
    client.post(
        f"/api/files/{file_id}/versions",
        data={"file": (io.BytesIO(b"Second Version Content"), "history.txt")},
        content_type="multipart/form-data",
        headers=auth_headers
    )

    ver_res = client.get(f"/api/files/{file_id}/versions", headers=auth_headers)
    versions = ver_res.get_json()["versions"]
    v1_id = [v["id"] for v in versions if v["version_number"] == 1][0]
    v2_id = [v["id"] for v in versions if v["version_number"] == 2][0]

    # Download v1 specifically
    dl_v1 = client.get(f"/api/files/{file_id}/versions/{v1_id}/download", headers=auth_headers)
    assert dl_v1.status_code == 200
    assert dl_v1.data == b"First Version Content"

    # Download v2 specifically
    dl_v2 = client.get(f"/api/files/{file_id}/versions/{v2_id}/download", headers=auth_headers)
    assert dl_v2.status_code == 200
    assert dl_v2.data == b"Second Version Content"

def test_restore_version(client, auth_headers):
    """Test restoring an earlier version creates a new version with that content."""
    res1 = client.post(
        "/api/files",
        data={"file": (io.BytesIO(b"Original State v1"), "restore_test.txt")},
        content_type="multipart/form-data",
        headers=auth_headers
    )
    file_id = res1.get_json()["file"]["id"]

    # Upload v2
    client.post(
        f"/api/files/{file_id}/versions",
        data={"file": (io.BytesIO(b"Broken State v2"), "restore_test.txt")},
        content_type="multipart/form-data",
        headers=auth_headers
    )

    # Find v1 ID
    ver_res = client.get(f"/api/files/{file_id}/versions", headers=auth_headers)
    v1_id = [v["id"] for v in ver_res.get_json()["versions"] if v["version_number"] == 1][0]

    # Restore v1 -> creates v3
    restore_res = client.post(f"/api/files/{file_id}/versions/{v1_id}/restore", headers=auth_headers)
    assert restore_res.status_code == 200
    v3_data = restore_res.get_json()["version"]
    assert v3_data["version_number"] == 3
    assert v3_data["is_current"] is True

    # Check file download now returns v1 content as current
    current_dl = client.get(f"/api/files/{file_id}/download", headers=auth_headers)
    assert current_dl.status_code == 200
    assert current_dl.data == b"Original State v1"

def test_delete_old_version(client, auth_headers):
    """Test deleting an old version while preserving active version."""
    res1 = client.post(
        "/api/files",
        data={"file": (io.BytesIO(b"Version 1 Data"), "delete_ver.txt")},
        content_type="multipart/form-data",
        headers=auth_headers
    )
    file_id = res1.get_json()["file"]["id"]

    # Attempting to delete the only version fails
    ver_res1 = client.get(f"/api/files/{file_id}/versions", headers=auth_headers)
    v1_id = ver_res1.get_json()["versions"][0]["id"]
    del_fail = client.delete(f"/api/files/{file_id}/versions/{v1_id}", headers=auth_headers)
    assert del_fail.status_code == 400
    assert del_fail.get_json()["code"] == "CANNOT_DELETE_ONLY_VERSION"

    # Add v2
    client.post(
        f"/api/files/{file_id}/versions",
        data={"file": (io.BytesIO(b"Version 2 Data"), "delete_ver.txt")},
        content_type="multipart/form-data",
        headers=auth_headers
    )

    # Now deleting v1 succeeds
    del_v1 = client.delete(f"/api/files/{file_id}/versions/{v1_id}", headers=auth_headers)
    assert del_v1.status_code == 200

    # Verify only v2 remains
    ver_res2 = client.get(f"/api/files/{file_id}/versions", headers=auth_headers)
    assert len(ver_res2.get_json()["versions"]) == 1
    assert ver_res2.get_json()["versions"][0]["version_number"] == 2

def test_cross_user_version_isolation(client, auth_headers, second_auth_headers):
    """Test that User 2 cannot access, upload, or restore User 1's versions."""
    res1 = client.post(
        "/api/files",
        data={"file": (io.BytesIO(b"Secret User 1 Data"), "secret.txt")},
        content_type="multipart/form-data",
        headers=auth_headers
    )
    file_id = res1.get_json()["file"]["id"]

    # User 2 tries to list versions -> 404
    cross_list = client.get(f"/api/files/{file_id}/versions", headers=second_auth_headers)
    assert cross_list.status_code == 404

    # User 2 tries to upload new version -> 404
    cross_upload = client.post(
        f"/api/files/{file_id}/versions",
        data={"file": (io.BytesIO(b"Malicious injection"), "secret.txt")},
        content_type="multipart/form-data",
        headers=second_auth_headers
    )
    assert cross_upload.status_code == 404
