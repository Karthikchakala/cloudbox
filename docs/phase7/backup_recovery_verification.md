# CloudBox — Backup Recovery & Disaster Verification Runbook

This runbook specifies the operational procedures for verifying disaster recovery bundles without risking production application data.

---

## 1. Verification Principles

1. **Zero Production Mutation**: Automated verification tests MUST restore exclusively into an isolated test database (`cloudbox_db_test_dr`) and isolated test bucket (`cloudbox-uploads-test`).
2. **Cryptographic Proof**: Before restoring, the bundle's master SHA-256 hash and each entry in `manifest.json` are validated.
3. **Automated Resource Cleanup**: The temporary test database and test bucket are destroyed immediately upon verification completion.

---

## 2. Recovery Verification Workflow

```bash
# 1. Run Dry-Run Validation (Checksum & Manifest validation without writing data)
python scripts/restore_manager.py --dry-run

# 2. Run Isolated Restore Verification (Full end-to-end restore into temporary DB/bucket)
python scripts/restore_manager.py --isolated

# 3. Automated Backup & Recovery Verification Pipeline
python scripts/backup_sync.py --verify-recovery
```

---

## 3. Interpreting Verification Outputs

### Success Output Example
```text
======================================================================
  CLOUDBOX DISASTER RECOVERY RESTORATION
  Bundle: cloudbox_backup_20260929_121834.tar.gz
  Mode: ISOLATED TEST RESTORE
======================================================================
[*] 1/4 Verifying master bundle checksum...
    [+] Master checksum valid: 76f2fcf1707af292...
[*] 2/4 Extracting & verifying manifest.json...
    [+] Database dump integrity verified.
    [+] All storage object checksums verified.
[*] 3/4 Creating isolated test database 'cloudbox_db_test_dr'...
[*] 3/4 Restoring PostgreSQL database into 'cloudbox_db_test_dr'...
[*] 4/4 Restoring MinIO objects into 'cloudbox-uploads-test'...
[+] ISOLATED TEST RESTORE VERIFIED: Data successfully restored to 'cloudbox_db_test_dr' and 'cloudbox-uploads-test'.
    [+] Cleaned up temporary test database.
```

### Telemetry Record (`backups/backup_status.json`)
```json
{
  "last_run_timestamp": "2026-09-29T12:18:37.150843+00:00",
  "status": "SUCCESS",
  "duration_seconds": 4.12,
  "bundle": {
    "name": "cloudbox_backup_20260929_121834.tar.gz",
    "size_bytes": 32054
  },
  "remote_replication": {
    "success": true,
    "status": "LOCAL_ONLY"
  },
  "recovery_verification": {
    "executed": true,
    "passed": true
  }
}
```
