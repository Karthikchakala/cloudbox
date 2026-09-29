import io
import json
import pytest
from app.models.file import File
from app.models.file_version import FileVersion
from app.models.share_link import ShareLink
from app.extensions import db

def test_analytics_unauthorized(client):
    """Test that unauthenticated requests to analytics are rejected."""
    res = client.get("/api/analytics/overview")
    assert res.status_code == 401
    assert res.get_json()["code"] == "UNAUTHORIZED"

def test_analytics_empty_user_state(client, auth_headers):
    """Test analytics overview when user has zero files."""
    res = client.get("/api/analytics/overview", headers=auth_headers)
    assert res.status_code == 200
    data = res.get_json()
    assert data["status"] == "success"
    assert data["summary"]["active_files_count"] == 0
    assert data["summary"]["active_storage_bytes"] == 0
    assert data["summary"]["trash_files_count"] == 0
    assert data["summary"]["total_shares_count"] == 0
    assert data["summary"]["active_shares_count"] == 0
    assert len(data["file_type_distribution"]) > 0
    assert len(data["upload_timeline"]) == 0

def test_analytics_with_files_and_categories(client, auth_headers, test_user):
    """Test analytics overview correctly calculates storage, categories, and versions."""
    # 1. Upload a Document
    res1 = client.post(
        "/api/files",
        headers=auth_headers,
        data={"file": (io.BytesIO(b"Quarterly financial report content"), "report.pdf")},
        content_type="multipart/form-data",
    )
    assert res1.status_code == 201
    file1_id = res1.get_json()["file"]["id"]

    # 2. Upload an Image
    res2 = client.post(
        "/api/files",
        headers=auth_headers,
        data={"file": (io.BytesIO(b"PNG IMAGE BYTES 123456"), "diagram.png")},
        content_type="multipart/form-data",
    )
    assert res2.status_code == 201
    file2_id = res2.get_json()["file"]["id"]

    # 3. Upload a new version to file1
    res_v2 = client.post(
        f"/api/files/{file1_id}/versions",
        headers=auth_headers,
        data={"file": (io.BytesIO(b"Updated financial report content with extra bytes"), "report_v2.pdf")},
        content_type="multipart/form-data",
    )
    assert res_v2.status_code == 201

    # 4. Create a share link on file1
    res_share = client.post(
        f"/api/files/{file1_id}/shares",
        headers=auth_headers,
        json={"permission": "download", "max_downloads": 5}
    )
    assert res_share.status_code == 201

    # 5. Move file2 to recycle bin
    res_trash = client.delete(f"/api/files/{file2_id}", headers=auth_headers)
    assert res_trash.status_code == 200

    # 6. Fetch analytics
    res_analytics = client.get("/api/analytics/overview", headers=auth_headers)
    assert res_analytics.status_code == 200
    data = res_analytics.get_json()

    summary = data["summary"]
    assert summary["active_files_count"] == 1  # file1 only (file2 is in trash)
    assert summary["trash_files_count"] == 1   # file2
    assert summary["total_versions_count"] >= 2 # file1 has 2 versions
    assert summary["total_shares_count"] == 1
    assert summary["active_shares_count"] == 1

    # Check distribution
    dist = {item["category"]: item for item in data["file_type_distribution"]}
    assert "Documents" in dist
    assert dist["Documents"]["count"] == 1
    assert dist["Documents"]["size_bytes"] > 0
    assert "Images" in dist

    # Check upload timeline
    assert len(data["upload_timeline"]) >= 1

def test_analytics_user_isolation(client, auth_headers, second_auth_headers):
    """Test that analytics metrics do not leak across users."""
    # User 1 uploads a file
    client.post(
        "/api/files",
        headers=auth_headers,
        data={"file": (io.BytesIO(b"User1 sensitive content"), "user1_secret.txt")},
        content_type="multipart/form-data",
    )

    # User 2 checks analytics
    res2 = client.get("/api/analytics/overview", headers=second_auth_headers)
    assert res2.status_code == 200
    data2 = res2.get_json()
    assert data2["summary"]["active_files_count"] == 0
    assert data2["summary"]["active_storage_bytes"] == 0
