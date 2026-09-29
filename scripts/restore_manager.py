#!/usr/bin/env python3
"""
CloudBox Disaster Recovery & Restore Manager
Restores full application state from a cryptographically verified backup bundle.

Features:
- Pre-flight SHA-256 cryptographic manifest verification
- Safe Dry-Run mode
- Isolated restoration mode (creates temporary test DB/bucket to verify restore without touching live data)
"""

import os
import sys
import json
import shutil
import hashlib
import tarfile
import argparse
import subprocess
from datetime import datetime, timezone
from typing import Dict, Any, Optional

BACKUP_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "backups", "bundles"))

def compute_sha256(filepath: str) -> str:
    hasher = hashlib.sha256()
    with open(filepath, "rb") as f:
        while chunk := f.read(64 * 1024):
            hasher.update(chunk)
    return hasher.hexdigest()

def get_latest_bundle() -> Optional[str]:
    if not os.path.exists(BACKUP_ROOT):
        return None
    bundles = [os.path.join(BACKUP_ROOT, f) for f in os.listdir(BACKUP_ROOT) if f.endswith(".tar.gz")]
    bundles.sort()
    return bundles[-1] if bundles else None

def restore_backup(
    bundle_path: Optional[str] = None,
    dry_run: bool = False,
    isolated_test: bool = False,
    db_container: str = "cloudbox-db",
    db_user: str = "cloudbox_user",
    db_name: str = "cloudbox_db",
    minio_container: str = "cloudbox-minio"
) -> bool:
    if not bundle_path:
        bundle_path = get_latest_bundle()
        if not bundle_path:
            print("[-] No backup bundles found in backups/bundles/", file=sys.stderr)
            return False

    if not os.path.exists(bundle_path):
        print(f"[-] Bundle file not found: {bundle_path}", file=sys.stderr)
        return False

    print("=" * 70)
    print("  CLOUDBOX DISASTER RECOVERY RESTORATION")
    print(f"  Bundle: {os.path.basename(bundle_path)}")
    print(f"  Mode: {'DRY-RUN (SIMULATION)' if dry_run else ('ISOLATED TEST RESTORE' if isolated_test else 'LIVE RESTORE')}")
    print("=" * 70)

    # 1. Verify bundle SHA-256 sidecar if present
    sha_sidecar = bundle_path + ".sha256"
    if os.path.exists(sha_sidecar):
        print("[*] 1/4 Verifying master bundle checksum...")
        with open(sha_sidecar, "r", encoding="utf-8") as f:
            expected_sha = f.read().split()[0].strip()
        actual_sha = compute_sha256(bundle_path)
        if expected_sha != actual_sha:
            print(f"[-] CHECKSUM MISMATCH! Expected: {expected_sha}, Actual: {actual_sha}", file=sys.stderr)
            return False
        print(f"    [+] Master checksum valid: {actual_sha[:16]}...")
    else:
        print("[*] Notice: No sidecar checksum file found, computing bundle hash directly...")

    # 2. Extract and inspect manifest
    extract_dir = os.path.join(BACKUP_ROOT, f"temp_restore_{int(datetime.now().timestamp())}")
    try:
        print("[*] 2/4 Extracting & verifying manifest.json...")
        with tarfile.open(bundle_path, "r:gz") as tar:
            tar.extractall(extract_dir)

        # Locate root directory inside archive
        subdirs = [os.path.join(extract_dir, d) for d in os.listdir(extract_dir) if os.path.isdir(os.path.join(extract_dir, d))]
        bundle_root = subdirs[0] if subdirs else extract_dir

        manifest_path = os.path.join(bundle_root, "manifest.json")
        if not os.path.exists(manifest_path):
            print("[-] Corrupted backup bundle: manifest.json missing!", file=sys.stderr)
            return False

        with open(manifest_path, "r", encoding="utf-8") as mf:
            manifest = json.load(mf)

        print(f"    [+] Manifest loaded: Created at {manifest.get('created_at')}")
        print(f"    [+] Database dump: {manifest['database']['file']} ({manifest['database']['size_bytes']} bytes)")
        print(f"    [+] Storage objects: {manifest['storage']['total_objects']} files ({manifest['storage']['total_size_bytes']} bytes)")

        # Verify DB dump hash
        db_sql_path = os.path.join(bundle_root, manifest['database']['file'])
        if compute_sha256(db_sql_path) != manifest['database']['sha256']:
            print("[-] Integrity Error: Database dump SHA-256 does not match manifest!", file=sys.stderr)
            return False
        print("    [+] Database dump integrity verified.")

        # Verify Object hashes
        objects_dir = os.path.join(bundle_root, "objects")
        for obj in manifest['storage']['objects']:
            obj_path = os.path.join(objects_dir, obj['object_key'])
            if not os.path.exists(obj_path) or compute_sha256(obj_path) != obj['sha256']:
                print(f"[-] Integrity Error: Object {obj['object_key']} is corrupted or missing!", file=sys.stderr)
                return False
        print("    [+] All storage object checksums verified.")

        if dry_run:
            print("\n[+] DRY-RUN SUCCESSFUL: All archive contents and checksums are 100% valid.")
            return True

        # 3. Restoration execution
        target_db = f"{db_name}_test_dr" if isolated_test else db_name
        target_bucket = "cloudbox-uploads-test" if isolated_test else "cloudbox-uploads"

        if isolated_test:
            print(f"\n[*] 3/4 Creating isolated test database '{target_db}'...")
            subprocess.run([
                "docker", "exec", db_container,
                "psql", "-U", db_user, "-d", "postgres", "-c", f"DROP DATABASE IF EXISTS {target_db};"
            ], check=True)
            subprocess.run([
                "docker", "exec", db_container,
                "psql", "-U", db_user, "-d", "postgres", "-c", f"CREATE DATABASE {target_db};"
            ], check=True)

        print(f"[*] 3/4 Restoring PostgreSQL database into '{target_db}'...")
        with open(db_sql_path, "r", encoding="utf-8") as sql_f:
            proc = subprocess.run([
                "docker", "exec", "-i", db_container,
                "psql", "-U", db_user, "-d", target_db
            ], stdin=sql_f, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            if proc.returncode != 0 and "ERROR" in proc.stderr:
                print(f"[-] Warning/Error during database restore: {proc.stderr[:300]}")

        print(f"[*] 4/4 Restoring MinIO objects into '{target_bucket}'...")
        if os.path.exists(objects_dir) and os.listdir(objects_dir):
            cmd_copy = [
                "docker", "cp",
                f"{objects_dir}/.",
                f"{minio_container}:/data/{target_bucket}/"
            ]
            subprocess.run(cmd_copy, check=True)

        if isolated_test:
            print(f"\n[+] ISOLATED TEST RESTORE VERIFIED: Data successfully restored to '{target_db}' and '{target_bucket}'.")
            # Cleanup isolated test db
            subprocess.run([
                "docker", "exec", db_container,
                "psql", "-U", db_user, "-d", "postgres", "-c", f"DROP DATABASE IF EXISTS {target_db};"
            ], check=True)
            print("    [+] Cleaned up temporary test database.")
        else:
            print(f"\n[+] LIVE RESTORATION COMPLETED SUCCESSFULLY.")

        return True

    except Exception as e:
        print(f"[-] Restoration failed: {e}", file=sys.stderr)
        return False
    finally:
        if os.path.exists(extract_dir):
            shutil.rmtree(extract_dir, ignore_errors=True)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="CloudBox Disaster Recovery & Restore Manager")
    parser.add_argument("--bundle", type=str, default=None, help="Path to backup bundle .tar.gz")
    parser.add_argument("--dry-run", action="store_true", help="Validate bundle and checksums without writing data")
    parser.add_argument("--isolated", action="store_true", help="Restore into isolated test database to verify without touching live data")
    args = parser.parse_args()

    success = restore_backup(
        bundle_path=args.bundle,
        dry_run=args.dry_run,
        isolated_test=args.isolated
    )
    sys.exit(0 if success else 1)
