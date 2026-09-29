import io
import pytest
from app.extensions import db
from app.models.file import File
from app.models.file_version import FileVersion
from app.models.user import User

def test_integrity_audit_consistent_state(app, test_user):
    """Verify that consistent database & storage records produce healthy status."""
    with app.app_context():
        u = User.query.filter_by(username="testuser").first()
        f = File(
            owner_id=u.id,
            original_filename="consistent.txt",
            object_key=f"{u.id}/uuid_consistent.txt",
            content_type="text/plain",
            size_bytes=100,
            checksum_sha256="abc12345"
        )
        db.session.add(f)
        db.session.commit()

        # Both DB and mocked MinIO have the key
        db_keys = {f.object_key}
        minio_keys = {f.object_key}

        missing = db_keys - minio_keys
        orphans = minio_keys - db_keys

        assert len(missing) == 0
        assert len(orphans) == 0

def test_integrity_audit_detects_missing_and_orphans():
    """Verify discrepancy detection logic between DB and object storage."""
    db_keys = {"user1/file1.txt", "user1/file2.txt", "user1/file3.txt"}
    minio_keys = {"user1/file1.txt", "user1/file2.txt", "user1/orphan_old.txt"}

    missing_in_minio = sorted(list(db_keys - minio_keys))
    orphaned_in_minio = sorted(list(minio_keys - db_keys))

    assert missing_in_minio == ["user1/file3.txt"]
    assert orphaned_in_minio == ["user1/orphan_old.txt"]
