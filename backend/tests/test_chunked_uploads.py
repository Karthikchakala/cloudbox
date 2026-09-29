import io
import pytest

def test_initiate_chunked_upload_success(client, auth_headers):
    """Test initiating a chunked upload session."""
    payload = {
        "filename": "database_archive.tar.gz",
        "file_size": 15 * 1024 * 1024, # 15 MB
        "chunk_size": 5 * 1024 * 1024, # 5 MB per chunk
        "content_type": "application/gzip"
    }

    res = client.post("/api/uploads/initiate", headers=auth_headers, json=payload)
    assert res.status_code == 201
    data = res.get_json()
    assert "upload_id" in data
    assert data["session"]["total_chunks"] == 3
    assert data["session"]["filename"] == "database_archive.tar.gz"

def test_chunked_upload_and_complete_flow(client, auth_headers):
    """Test full cycle: initiate -> upload 3 chunks -> verify status -> complete assembly."""
    chunk1_data = b"CHUNK1_CONTENT_AAAA_" * 100
    chunk2_data = b"CHUNK2_CONTENT_BBBB_" * 100
    total_size = len(chunk1_data) + len(chunk2_data)

    # 1. Initiate
    res_init = client.post("/api/uploads/initiate", headers=auth_headers, json={
        "filename": "large_dataset.csv",
        "file_size": total_size,
        "chunk_size": len(chunk1_data),
        "content_type": "text/csv"
    })
    assert res_init.status_code == 201
    upload_id = res_init.get_json()["upload_id"]

    # 2. Upload Chunk 1
    res_c1 = client.put(
        f"/api/uploads/{upload_id}/chunks/1",
        headers=auth_headers,
        data=chunk1_data,
        content_type="application/octet-stream"
    )
    assert res_c1.status_code == 200
    assert res_c1.get_json()["uploaded_chunks_count"] == 1

    # 3. Upload Chunk 2
    res_c2 = client.put(
        f"/api/uploads/{upload_id}/chunks/2",
        headers=auth_headers,
        data=chunk2_data,
        content_type="application/octet-stream"
    )
    assert res_c2.status_code == 200
    assert res_c2.get_json()["uploaded_chunks_count"] == 2

    # 4. Check Status
    res_status = client.get(f"/api/uploads/{upload_id}", headers=auth_headers)
    assert res_status.status_code == 200
    assert res_status.get_json()["session"]["progress_percent"] == 100.0

    # 5. Complete Upload
    res_comp = client.post(f"/api/uploads/{upload_id}/complete", headers=auth_headers)
    assert res_comp.status_code == 201
    file_info = res_comp.get_json()["file"]
    assert file_info["original_filename"] == "large_dataset.csv"
    assert file_info["size_bytes"] == total_size

def test_chunked_upload_missing_chunks_rejection(client, auth_headers):
    """Test completing an upload before uploading all chunks is rejected."""
    res_init = client.post("/api/uploads/initiate", headers=auth_headers, json={
        "filename": "broken_upload.dat",
        "file_size": 1000,
        "chunk_size": 500,
        "content_type": "application/octet-stream"
    })
    upload_id = res_init.get_json()["upload_id"]

    # Upload chunk 1 only
    client.put(f"/api/uploads/{upload_id}/chunks/1", headers=auth_headers, data=b"A" * 500)

    # Attempt complete (chunk 2 missing)
    res_comp = client.post(f"/api/uploads/{upload_id}/complete", headers=auth_headers)
    assert res_comp.status_code == 400
    assert res_comp.get_json()["code"] == "INCOMPLETE_CHUNKS"

def test_cancel_chunked_upload(client, auth_headers):
    """Test cancelling an active upload session."""
    res_init = client.post("/api/uploads/initiate", headers=auth_headers, json={
        "filename": "abandoned.zip",
        "file_size": 2000,
        "chunk_size": 1000
    })
    upload_id = res_init.get_json()["upload_id"]

    res_cancel = client.delete(f"/api/uploads/{upload_id}", headers=auth_headers)
    assert res_cancel.status_code == 200
    assert res_cancel.get_json()["status"] == "aborted"
