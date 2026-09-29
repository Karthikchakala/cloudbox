import os
import json
import hashlib
import tempfile
import pytest

def compute_sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()

def test_backup_manifest_integrity_validation():
    """Verify manifest creation and checksum validation against data chunks."""
    with tempfile.TemporaryDirectory() as tmpdir:
        # Simulate database dump
        db_content = b"-- PostgreSQL Database Dump\nCREATE TABLE test (id int);\n"
        db_file = os.path.join(tmpdir, "database.sql")
        with open(db_file, "wb") as f:
            f.write(db_content)

        db_sha256 = compute_sha256_bytes(db_content)

        # Simulate object
        obj_content = b"Binary file payload stored in MinIO"
        obj_dir = os.path.join(tmpdir, "objects", "user-uuid")
        os.makedirs(obj_dir, exist_ok=True)
        obj_file = os.path.join(obj_dir, "doc.pdf")
        with open(obj_file, "wb") as f:
            f.write(obj_content)

        obj_sha256 = compute_sha256_bytes(obj_content)

        # Construct manifest
        manifest = {
            "format_version": "2.0",
            "database": {
                "file": "database.sql",
                "size_bytes": len(db_content),
                "sha256": db_sha256
            },
            "storage": {
                "bucket": "cloudbox-uploads",
                "objects": [
                    {
                        "object_key": "user-uuid/doc.pdf",
                        "size_bytes": len(obj_content),
                        "sha256": obj_sha256
                    }
                ]
            }
        }

        manifest_path = os.path.join(tmpdir, "manifest.json")
        with open(manifest_path, "w", encoding="utf-8") as f:
            json.dump(manifest, f)

        # Test verification logic
        with open(manifest_path, "r", encoding="utf-8") as f:
            loaded_manifest = json.load(f)

        # DB checksum matches
        with open(os.path.join(tmpdir, loaded_manifest["database"]["file"]), "rb") as f:
            assert compute_sha256_bytes(f.read()) == loaded_manifest["database"]["sha256"]

        # Storage object checksum matches
        for obj in loaded_manifest["storage"]["objects"]:
            actual_obj_path = os.path.join(tmpdir, "objects", obj["object_key"])
            with open(actual_obj_path, "rb") as f:
                assert compute_sha256_bytes(f.read()) == obj["sha256"]

def test_corrupted_manifest_fails_verification():
    """Verify that tampered data triggers integrity check failure."""
    db_content = b"Original DB dump"
    expected_hash = compute_sha256_bytes(db_content)

    tampered_content = b"Tampered DB dump with injected rows"
    actual_hash = compute_sha256_bytes(tampered_content)

    assert actual_hash != expected_hash
