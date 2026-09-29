# CloudBox — Off-Site Backup & Multi-Cloud Replication Guide

This guide describes how CloudBox replicates verified cryptographic backup bundles to external S3-compatible cloud storage (AWS S3, Cloudflare R2, Wasabi, or a secondary MinIO instance).

---

## 1. Replication Architecture & Security Model

```mermaid
sequenceDiagram
    participant App as CloudBox Backup Manager
    participant Local as Local Storage (backups/bundles/)
    participant Remote as Remote Storage (AWS S3 / R2)
    participant DR as Isolated Test Environment

    App->>Local: Generate unified bundle (DB + MinIO objects + manifest.json)
    App->>Local: Calculate and verify master SHA-256 sidecar
    Note over App,Local: Local backup secured & immutable
    App->>Remote: Upload bundle.tar.gz + bundle.sha256 over TLS (S3 API)
    App->>Remote: Verify remote object size & ETag
    App->>Remote: Apply retention policy (prune bundles > N count)
    opt Recovery Verification
        App->>DR: Restore bundle to isolated DB & test bucket
        App->>DR: Confirm table row counts & object checksums
        App->>DR: Clean up isolated test resources
    end
    App->>Local: Record status in backups/backup_status.json
```

---

## 2. Supported Remote Storage Providers

### Option A: AWS S3
```ini
REMOTE_BACKUP_ENABLED=true
REMOTE_BACKUP_S3_ENDPOINT=s3.amazonaws.com
REMOTE_BACKUP_BUCKET=my-cloudbox-offsite-backups
REMOTE_BACKUP_ACCESS_KEY=AKIAXXXXXXXXXXXXXXXX
REMOTE_BACKUP_SECRET_KEY=wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY
REMOTE_BACKUP_REGION=us-east-1
BACKUP_RETENTION_COUNT=14
```

### Option B: Cloudflare R2 (Zero Egress Fees)
```ini
REMOTE_BACKUP_ENABLED=true
REMOTE_BACKUP_S3_ENDPOINT=<account_id>.r2.cloudflarestorage.com
REMOTE_BACKUP_BUCKET=my-cloudbox-r2-backups
REMOTE_BACKUP_ACCESS_KEY=<r2_access_key_id>
REMOTE_BACKUP_SECRET_KEY=<r2_secret_access_key>
REMOTE_BACKUP_REGION=auto
BACKUP_RETENTION_COUNT=14
```

---

## 3. Least-Privilege IAM Policy for Remote Storage

Grant only the minimum required S3 permissions:

```json
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Sid": "CloudBoxBackupReplication",
            "Effect": "Allow",
            "Action": [
                "s3:ListBucket",
                "s3:GetBucketLocation"
            ],
            "Resource": "arn:aws:s3:::my-cloudbox-offsite-backups"
        },
        {
            "Sid": "CloudBoxObjectManagement",
            "Effect": "Allow",
            "Action": [
                "s3:PutObject",
                "s3:GetObject",
                "s3:DeleteObject"
            ],
            "Resource": "arn:aws:s3:::my-cloudbox-offsite-backups/*"
        }
    ]
}
```

---

## 4. Execution Commands

```bash
# Standard local backup + offsite replication
python scripts/backup_sync.py

# Full pipeline: Local backup + offsite replication + isolated recovery verification
python scripts/backup_sync.py --verify-recovery
```
