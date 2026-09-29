import os
import json
import pytest
from app.services.remote_backup_service import RemoteBackupService

def test_prometheus_metrics_endpoint_format(client, auth_headers):
    """Verify that /api/metrics/prometheus returns valid Prometheus exposition text."""
    res = client.get("/api/metrics/prometheus")
    assert res.status_code == 200
    assert "text/plain" in res.content_type

    text = res.get_data(as_text=True)
    assert "# HELP cloudbox_uptime_seconds" in text
    assert "cloudbox_uptime_seconds" in text
    assert "cloudbox_db_up 1" in text
    assert "cloudbox_users_total" in text
    assert "cloudbox_files_total" in text
    assert "cloudbox_cache_hits_total" in text
    assert "cloudbox_cache_misses_total" in text
    assert "cloudbox_backup_latest_status" in text

def test_remote_backup_service_local_fallback(tmp_path):
    """Verify that remote backup service preserves local file when remote is disabled."""
    test_bundle = tmp_path / "cloudbox_backup_test.tar.gz"
    test_bundle.write_bytes(b"dummy archive data")

    service = RemoteBackupService()
    service.enabled = False

    result = service.replicate_bundle(str(test_bundle))
    assert result["success"] is True
    assert result["status"] == "LOCAL_ONLY"
    assert result["bundle"] == "cloudbox_backup_test.tar.gz"
    assert test_bundle.exists()

def test_remote_backup_service_missing_file():
    """Verify that replicating a nonexistent bundle returns graceful failure."""
    service = RemoteBackupService()
    result = service.replicate_bundle("/nonexistent/bundle.tar.gz")
    assert result["success"] is False
    assert "not found" in result["error"].lower()
