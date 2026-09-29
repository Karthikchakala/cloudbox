#!/usr/bin/env python3
"""
CloudBox Storage Integrity & Consistency Audit Tool
Reconciles PostgreSQL metadata records with MinIO object storage.

Features:
- Audits File & FileVersion records vs MinIO objects in 'cloudbox-uploads'
- Identifies missing storage objects (DB record exists, MinIO object missing)
- Identifies orphaned objects (MinIO object exists, no DB record)
- Identifies checksum discrepancies
- Identifies stale/interrupted chunk staging files
- Safe dry-run mode by default
- Explicit confirmation required for any destructive repair actions
"""

import os
import sys
import json
import argparse
from datetime import datetime, timezone
from typing import Dict, List, Any

# Ensure backend app imports work if run inside container or locally with PYTHONPATH
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "backend")))

def run_integrity_audit(deep_checksum: bool = False, repair: bool = False, auto_confirm: bool = False) -> Dict[str, Any]:
    try:
        from app import create_app
        from app.extensions import db
        from app.models.file import File
        from app.models.file_version import FileVersion
        from app.models.upload_session import UploadSession
        from app.services.storage_service import storage_service
    except ImportError as e:
        print(f"[-] Error loading CloudBox backend modules: {e}", file=sys.stderr)
        print("[-] Ensure PYTHONPATH points to backend directory or run inside backend container.", file=sys.stderr)
        sys.exit(1)

    app = create_app()
    with app.app_context():
        print("=" * 70)
        print("  CLOUDBOX DATA INTEGRITY & STORAGE AUDIT")
        print(f"  Timestamp: {datetime.now(timezone.utc).isoformat()}")
        print(f"  Mode: {'REPAIR' if repair else 'AUDIT (DRY-RUN)'}")
        print("=" * 70)

        # 1. Fetch DB Metadata
        print("[*] 1/4 Scanning PostgreSQL metadata records...")
        files = File.query.all()
        versions = FileVersion.query.all()
        sessions = UploadSession.query.all()

        db_file_keys = set()
        db_version_keys = set()
        db_thumbnail_keys = set()
        db_records_by_key = {}

        for f in files:
            if f.object_key:
                db_file_keys.add(f.object_key)
                db_records_by_key.setdefault(f.object_key, []).append({"type": "file", "id": str(f.id), "name": f.original_filename, "deleted": f.deleted_at is not None})
            if f.thumbnail_object_key:
                db_thumbnail_keys.add(f.thumbnail_object_key)
                db_records_by_key.setdefault(f.thumbnail_object_key, []).append({"type": "thumbnail", "id": str(f.id)})

        for v in versions:
            if v.object_key:
                db_version_keys.add(v.object_key)
                db_records_by_key.setdefault(v.object_key, []).append({"type": "version", "file_id": str(v.file_id), "version": v.version_number})

        active_upload_ids = {str(s.id) for s in sessions if s.status in ("initiated", "uploading")}
        all_db_keys = db_file_keys.union(db_version_keys).union(db_thumbnail_keys)
        print(f"    Total DB Files: {len(files)}, FileVersions: {len(versions)}, Unique Expected Keys: {len(all_db_keys)}")

        # 2. Fetch MinIO Objects
        print("[*] 2/4 Scanning MinIO object storage bucket...")
        minio_objects = {}
        try:
            client = storage_service.client
            bucket = storage_service.bucket_name
            objects = client.list_objects(bucket, recursive=True)
            for obj in objects:
                minio_objects[obj.object_name] = {
                    "size": obj.size,
                    "last_modified": obj.last_modified.isoformat() if obj.last_modified else None,
                    "etag": obj.etag
                }
            print(f"    Total MinIO Objects found: {len(minio_objects)}")
        except Exception as e:
            print(f"[-] Failed scanning MinIO bucket: {e}", file=sys.stderr)
            sys.exit(1)

        # 3. Analyze Discrepancies
        print("[*] 3/4 Analyzing storage consistency...")
        missing_in_storage = []
        orphaned_in_storage = []
        stale_chunks = []
        checksum_discrepancies = []

        # Check DB keys in MinIO
        for key in all_db_keys:
            if key not in minio_objects:
                missing_in_storage.append({
                    "object_key": key,
                    "references": db_records_by_key.get(key, [])
                })

        # Check MinIO objects in DB
        for key, meta in minio_objects.items():
            if key.startswith("chunks/"):
                parts = key.split("/")
                upload_id = parts[1] if len(parts) > 1 else ""
                if upload_id not in active_upload_ids:
                    stale_chunks.append({
                        "object_key": key,
                        "upload_id": upload_id,
                        "size": meta["size"]
                    })
            elif key not in all_db_keys:
                orphaned_in_storage.append({
                    "object_key": key,
                    "size": meta["size"],
                    "last_modified": meta["last_modified"]
                })

        # Checksum Verification (if deep check requested)
        if deep_checksum and not missing_in_storage:
            print("[*] Performing deep SHA-256 integrity verification...")
            for f in files:
                if f.object_key in minio_objects and f.checksum_sha256:
                    try:
                        stream = storage_service.get_file_stream(f.object_key)
                        if stream:
                            content = b"".join(stream.stream(32 * 1024))
                            actual_hash = storage_service.compute_sha256(content)
                            if actual_hash != f.checksum_sha256:
                                checksum_discrepancies.append({
                                    "file_id": str(f.id),
                                    "object_key": f.object_key,
                                    "expected_sha256": f.checksum_sha256,
                                    "actual_sha256": actual_hash
                                })
                    except Exception as e:
                        print(f"    [-] Checksum check error on {f.object_key}: {e}")

        # Summary
        is_consistent = (
            len(missing_in_storage) == 0 and
            len(orphaned_in_storage) == 0 and
            len(stale_chunks) == 0 and
            len(checksum_discrepancies) == 0
        )

        results = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "status": "HEALTHY" if is_consistent else "DISCREPANCIES_DETECTED",
            "stats": {
                "total_db_files": len(files),
                "total_db_versions": len(versions),
                "total_minio_objects": len(minio_objects),
                "missing_in_storage_count": len(missing_in_storage),
                "orphaned_in_storage_count": len(orphaned_in_storage),
                "stale_chunks_count": len(stale_chunks),
                "checksum_discrepancies_count": len(checksum_discrepancies)
            },
            "missing_in_storage": missing_in_storage,
            "orphaned_in_storage": orphaned_in_storage,
            "stale_chunks": stale_chunks,
            "checksum_discrepancies": checksum_discrepancies
        }

        print("\n" + "-" * 70)
        print("  AUDIT SUMMARY")
        print("-" * 70)
        print(f"  System State:           {'[✓] CONSISTENT & HEALTHY' if is_consistent else '[!] DISCREPANCIES DETECTED'}")
        print(f"  Missing Objects:        {len(missing_in_storage)}")
        print(f"  Orphaned Objects:       {len(orphaned_in_storage)}")
        print(f"  Stale Upload Chunks:    {len(stale_chunks)}")
        print(f"  Checksum Discrepancies: {len(checksum_discrepancies)}")
        print("-" * 70)

        # 4. Repair Execution (if requested)
        if repair and not is_consistent:
            print("\n[*] 4/4 Repair Mode Requested.")
            if not auto_confirm:
                print("\n[!] CAUTION: Repair will permanently purge orphaned objects and stale chunks.")
                conf = input("Type 'CONFIRM' to proceed with repairs: ").strip()
                if conf != "CONFIRM":
                    print("[-] Repair aborted by user.")
                    return results

            print("[*] Executing safe repairs...")
            repaired_chunks = 0
            for chunk in stale_chunks:
                try:
                    storage_service.delete_file(chunk["object_key"])
                    repaired_chunks += 1
                except Exception as e:
                    print(f"    [-] Failed deleting chunk {chunk['object_key']}: {e}")

            repaired_orphans = 0
            for orphan in orphaned_in_storage:
                try:
                    storage_service.delete_file(orphan["object_key"])
                    repaired_orphans += 1
                except Exception as e:
                    print(f"    [-] Failed deleting orphan {orphan['object_key']}: {e}")

            print(f"[+] Repair completed: {repaired_chunks} stale chunks and {repaired_orphans} orphaned objects purged.")
            results["repair_summary"] = {
                "stale_chunks_purged": repaired_chunks,
                "orphaned_objects_purged": repaired_orphans
            }

        return results

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="CloudBox Storage Integrity & Consistency Audit")
    parser.add_argument("--deep", action="store_true", help="Perform byte-level SHA-256 checksum verification")
    parser.add_argument("--repair", action="store_true", help="Execute cleanup of orphaned and stale staging objects")
    parser.add_argument("--confirm-repair", action="store_true", help="Non-interactive confirmation for repair")
    parser.add_argument("--json", action="store_true", help="Output raw JSON results")
    args = parser.parse_args()

    audit_res = run_integrity_audit(
        deep_checksum=args.deep,
        repair=args.repair,
        auto_confirm=args.confirm_repair
    )

    if args.json:
        print(json.dumps(audit_res, indent=2))
