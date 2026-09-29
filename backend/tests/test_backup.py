import os
import json
import pytest
from app.models.file import File
from app.models.user import User
from app.extensions import db

def test_backup_metadata_and_export_simulation(client, auth_headers, test_user):
    """Test data export simulation and data consistency across backups."""
    # 1. Create file record
    f = File(
        owner_id=test_user.id,
        original_filename="financial_summary.xlsx",
        object_key=f"{test_user.id}/financial_summary.xlsx",
        content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        size_bytes=45200,
        checksum_sha256="e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
    )
    db.session.add(f)
    db.session.commit()

    # 2. Export database state snapshot
    user_records = [u.to_dict() for u in User.query.all()]
    file_records = [fil.to_dict() for fil in File.query.all()]

    snapshot = {
        "users": user_records,
        "files": file_records,
        "total_files": len(file_records)
    }

    assert snapshot["total_files"] == 1
    assert snapshot["files"][0]["original_filename"] == "financial_summary.xlsx"
    assert snapshot["files"][0]["size_bytes"] == 45200

def test_backup_retention_prune_logic(tmp_path):
    """Test backup retention policy correctly keeps only latest N backups."""
    backup_dir = tmp_path / "backups"
    backup_dir.mkdir()

    # Create 15 mock backup files
    for i in range(15):
        fn = backup_dir / f"backup_cloudbox_db_20260929_{i:02d}0000.sql"
        fn.write_text(f"-- SQL backup {i}")
        meta_fn = backup_dir / f"backup_cloudbox_db_20260929_{i:02d}0000.sql.meta"
        meta_fn.write_text(f"timestamp=20260929_{i:02d}0000\n")

    files = sorted([f for f in os.listdir(backup_dir) if f.endswith(".sql")])
    assert len(files) == 15

    # Apply retention policy of 5
    retention_count = 5
    to_delete = files[:-retention_count]
    for f in to_delete:
        os.remove(backup_dir / f)
        os.remove(backup_dir / (f + ".meta"))

    remaining = [f for f in os.listdir(backup_dir) if f.endswith(".sql")]
    assert len(remaining) == 5
    assert "backup_cloudbox_db_20260929_140000.sql" in remaining
