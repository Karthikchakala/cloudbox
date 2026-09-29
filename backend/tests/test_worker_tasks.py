import io
import pytest
from PIL import Image
from app.models.file import File
from app.extensions import db

def test_file_processing_status_endpoint(client, auth_headers):
    """Test retrieving file processing status and metadata."""
    # 1. Upload sample text file
    res = client.post(
        "/api/files",
        headers=auth_headers,
        data={"file": (io.BytesIO(b"Processing test content"), "sample.txt")},
        content_type="multipart/form-data"
    )
    assert res.status_code == 201
    file_id = res.get_json()["file"]["id"]

    # 2. Get processing status
    res_status = client.get(f"/api/files/{file_id}/processing-status", headers=auth_headers)
    assert res_status.status_code == 200
    data = res_status.get_json()
    assert data["file_id"] == file_id
    assert "status" in data

def test_metrics_endpoint(client):
    """Test system operational metrics endpoint."""
    res = client.get("/api/metrics")
    assert res.status_code == 200
    data = res.get_json()
    assert "uptime_seconds" in data
    assert "cache" in data
    assert "database" in data
    assert data["features"]["chunked_uploads"] is True
