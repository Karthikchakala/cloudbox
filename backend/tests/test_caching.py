import io
import pytest
from app.services.cache_service import cache_service

def test_cache_service_set_get_and_delete():
    """Test standard cache operations."""
    key = "test:key:123"
    data = {"sample": "value", "count": 42}

    cache_service.set_json(key, data, ttl_seconds=60)
    retrieved = cache_service.get_json(key)
    if cache_service.is_available:
        assert retrieved == data
        assert retrieved["count"] == 42
        
        cache_service.delete(key)
        assert cache_service.get_json(key) is None

def test_file_listing_cache_hit_and_invalidation(client, auth_headers):
    """Test that file listing is cached and invalidated on new file upload."""
    # 1. First fetch (cache miss -> stored)
    res1 = client.get("/api/files", headers=auth_headers)
    assert res1.status_code == 200

    # 2. Upload file -> must invalidate cache
    res_up = client.post(
        "/api/files",
        headers=auth_headers,
        data={"file": (io.BytesIO(b"cached test content"), "cache_test.txt")},
        content_type="multipart/form-data"
    )
    assert res_up.status_code == 201

    # 3. Next fetch must contain the new file
    res2 = client.get("/api/files", headers=auth_headers)
    assert res2.status_code == 200
    filenames = [f["original_filename"] for f in res2.get_json()["files"]]
    assert "cache_test.txt" in filenames

def test_analytics_cache_user_isolation(client, auth_headers, second_auth_headers):
    """Test that cached analytics are strictly isolated per user."""
    res1 = client.get("/api/analytics/overview", headers=auth_headers)
    assert res1.status_code == 200

    res2 = client.get("/api/analytics/overview", headers=second_auth_headers)
    assert res2.status_code == 200

    # User 1 and User 2 usernames must differ
    assert res1.get_json()["username"] != res2.get_json()["username"]
