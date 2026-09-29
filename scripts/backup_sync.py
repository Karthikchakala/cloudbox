#!/usr/bin/env python3
"""
CloudBox Automated Backup & Off-Site Replication Manager
Executes unified backup creation, SHA-256 validation, offsite S3 replication,
and optional isolated recovery verification.

Usage:
  python scripts/backup_sync.py [--verify-recovery] [--dry-run]
"""

import os
import sys
import time
import json
import argparse
from datetime import datetime, timezone

# Add backend directory to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "backend")))
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__))))

from backup_manager import create_unified_backup
from restore_manager import restore_backup

STATUS_FILE = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "backups", "backup_status.json"))

def record_status(status_payload: dict):
    os.makedirs(os.path.dirname(STATUS_FILE), exist_ok=True)
    with open(STATUS_FILE, "w", encoding="utf-8") as f:
        json.dump(status_payload, f, indent=2)

def execute_backup_and_sync(verify_recovery: bool = False, max_retries: int = 3) -> bool:
    start_time = time.time()
    print("=" * 75)
    print("  CLOUDBOX AUTOMATED BACKUP, SYNC & DISASTER RECOVERY PIPELINE")
    print(f"  Timestamp: {datetime.now(timezone.utc).isoformat()}")
    print("=" * 75)

    # 1. Create Local Unified Backup Bundle
    print("[*] STEP 1: Generating local cryptographic backup bundle...")
    bundle_path = create_unified_backup()
    if not bundle_path or not os.path.exists(bundle_path):
        print("[-] Pipeline Failed: Local backup creation failed!", file=sys.stderr)
        record_status({
            "last_run_timestamp": datetime.now(timezone.utc).isoformat(),
            "status": "FAILED",
            "stage": "LOCAL_BACKUP",
            "duration_seconds": round(time.time() - start_time, 2),
            "error": "Failed generating local backup bundle"
        })
        return False

    bundle_filename = os.path.basename(bundle_path)
    bundle_size = os.path.getsize(bundle_path)
    print(f"[+] Local backup ready: {bundle_filename} ({bundle_size} bytes)")

    # 2. Remote Replication with Exponential Backoff Retries
    print("\n[*] STEP 2: Replicating backup bundle to offsite object storage...")
    try:
        import importlib.util
        service_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "backend", "app", "services", "remote_backup_service.py"))
        spec = importlib.util.spec_from_file_location("remote_backup_service", service_path)
        r_mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(r_mod)
        remote_backup_service = r_mod.remote_backup_service

        replication_result = None
        attempt = 0
        max_retries = 3
        backoff = 2

        while attempt < max_retries:
            attempt += 1
            print(f"    -> Upload attempt {attempt}/{max_retries}...")
            replication_result = remote_backup_service.replicate_bundle(bundle_path)
            if replication_result.get("success"):
                print(f"    [+] Replication status: {replication_result.get('status')} ({replication_result.get('message', 'OK')})")
                break
            else:
                print(f"    [!] Replication attempt {attempt} failed: {replication_result.get('error')}")
                if attempt < max_retries:
                    time.sleep(backoff)
                    backoff *= 2
    except Exception as e:
        replication_result = {"success": False, "error": str(e), "status": "FAILED"}
        print(f"[-] Remote replication error: {e}", file=sys.stderr)

    # 3. Optional Automated Isolated Recovery Verification
    recovery_verified = None
    if verify_recovery:
        print("\n[*] STEP 3: Executing Automated Isolated Recovery Verification...")
        recovery_verified = restore_backup(bundle_path=bundle_path, isolated_test=True)
        print(f"    [+] Recovery verification result: {'PASSED [OK]' if recovery_verified else 'FAILED [FAIL]'}")

    duration = round(time.time() - start_time, 2)
    pipeline_success = bool(bundle_path and replication_result.get("success", True) and (recovery_verified is not False))

    status_data = {
        "last_run_timestamp": datetime.now(timezone.utc).isoformat(),
        "status": "SUCCESS" if pipeline_success else "WARNING_OR_FAILED",
        "duration_seconds": duration,
        "bundle": {
            "name": bundle_filename,
            "size_bytes": bundle_size,
            "path": bundle_path
        },
        "remote_replication": replication_result,
        "recovery_verification": {
            "executed": verify_recovery,
            "passed": recovery_verified
        }
    }
    record_status(status_data)

    print("\n" + "=" * 75)
    print(f"  BACKUP PIPELINE COMPLETE: {'SUCCESS [OK]' if pipeline_success else 'COMPLETED WITH WARNINGS [!]'}")
    print(f"  Total Duration: {duration}s")
    print("=" * 75)
    return pipeline_success

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="CloudBox Automated Backup & Offsite Replication")
    parser.add_argument("--verify-recovery", action="store_true", help="Execute isolated database restoration test")
    parser.add_argument("--retries", type=int, default=3, help="Max upload retry attempts")
    args = parser.parse_args()

    success = execute_backup_and_sync(verify_recovery=args.verify_recovery, max_retries=args.retries)
    sys.exit(0 if success else 1)
