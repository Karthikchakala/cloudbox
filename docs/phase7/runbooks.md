# CloudBox — Operations Runbooks (Phase 7)

Comprehensive operational procedures and disaster recovery runbooks for CloudBox administrators and SREs.

---

## Runbook Index
1. [Initial Cloud VM Deployment](#1-initial-cloud-vm-deployment)
2. [Domain & HTTPS Configuration](#2-domain--https-configuration)
3. [Routine Backup & Remote Replication](#3-routine-backup--remote-replication)
4. [Off-Site Backup Verification](#4-off-site-backup-verification)
5. [Isolated Disaster Recovery Testing](#5-isolated-disaster-recovery-testing)
6. [Full System Disaster Recovery](#6-full-system-disaster-recovery)
7. [PostgreSQL Outage Response](#7-postgresql-outage-response)
8. [Redis Outage Response](#8-redis-outage-response)
9. [MinIO Storage Outage Response](#9-minio-storage-outage-response)
10. [Background Worker Failure Recovery](#10-background-worker-failure-recovery)
11. [Disk Space Exhaustion Mitigation](#11-disk-space-exhaustion-mitigation)
12. [TLS Certificate Renewal Failure](#12-tls-certificate-renewal-failure)
13. [Application Upgrade Procedure](#13-application-upgrade-procedure)
14. [Application Rollback Procedure](#14-application-rollback-procedure)
15. [Monitoring & Alert Troubleshooting](#15-monitoring--alert-troubleshooting)

---

### 1. Initial Cloud VM Deployment
* **Prerequisites**: Ubuntu Linux VM, Docker Engine, ports 80/443 open.
* **Commands**:
  ```bash
  git clone https://github.com/Karthikchakala/hospital-mgmt.git /opt/cloudbox
  cd /opt/cloudbox
  cp .env.example .env
  # Configure production secrets in .env
  docker compose -f compose.yaml -f compose.prod.yaml up -d --build
  bash scripts/health_check.sh
  ```
* **Validation**: Output shows `SYSTEM STATUS: ALL CHECKS PASSED [HEALTHY]`.

---

### 2. Domain & HTTPS Configuration
* **Prerequisites**: Domain A record pointing to server IP.
* **Commands**:
  ```bash
  docker run -it --rm \
    -v /opt/cloudbox/certbot/www:/var/www/certbot \
    -v /opt/cloudbox/certbot/conf:/etc/letsencrypt \
    certbot/certbot certonly --webroot -w /var/www/certbot \
    -d cloudbox.yourdomain.com --email admin@yourdomain.com --agree-tos
  docker compose restart nginx
  ```
* **Validation**: Navigating to `http://cloudbox.yourdomain.com` automatically redirects to `https://`.

---

### 3. Routine Backup & Remote Replication
* **Objective**: Create unified backup and sync to remote S3 storage.
* **Command**:
  ```bash
  python scripts/backup_sync.py
  ```
* **Expected Output**: Bundle created, master SHA-256 computed, remote replication status `REPLICATED` or `LOCAL_ONLY`.

---

### 4. Off-Site Backup Verification
* **Objective**: Confirm remote object existence and checksum match.
* **Command**:
  ```bash
  cat backups/backup_status.json
  ```
* **Validation**: `remote_replication.success` is `true`.

---

### 5. Isolated Disaster Recovery Testing
* **Objective**: Verify full database and object restore into temporary infrastructure without touching live data.
* **Command**:
  ```bash
  python scripts/restore_manager.py --isolated
  ```
* **Expected Output**: `ISOLATED TEST RESTORE VERIFIED: Data successfully restored to 'cloudbox_db_test_dr' and 'cloudbox-uploads-test'`.

---

### 6. Full System Disaster Recovery
* **Scenario**: Total host destruction or volume loss requiring restore to a new host.
* **Procedure**:
  1. Deploy fresh CloudBox stack (`docker compose up -d`).
  2. Download latest backup bundle `cloudbox_backup_<timestamp>.tar.gz` from remote S3.
  3. Execute live restore:
     ```bash
     python scripts/restore_manager.py --bundle backups/bundles/cloudbox_backup_<timestamp>.tar.gz
     ```
  4. Run storage integrity audit:
     ```bash
     docker compose exec -e PYTHONPATH=. backend python scripts/storage_integrity_audit.py --deep
     ```

---

### 7. PostgreSQL Outage Response
* **Symptoms**: Backend returns HTTP 500; `cloudbox_db_up` metric is `0`.
* **Action**:
  ```bash
  docker compose logs db --tail 50
  docker compose restart db
  docker compose exec backend curl -s http://localhost:5000/health
  ```

---

### 8. Redis Outage Response
* **Symptoms**: Cache misses 100%, but application continues serving files via DB fallback.
* **Action**:
  ```bash
  docker compose restart redis
  docker compose logs redis --tail 30
  ```

---

### 9. MinIO Storage Outage Response
* **Symptoms**: File upload/download endpoints return 500; S3 errors in backend logs.
* **Action**:
  ```bash
  docker compose restart minio
  docker compose exec backend python -c "from app.services.storage_service import storage_service; print(storage_service.ensure_bucket_exists())"
  ```

---

### 10. Background Worker Failure Recovery
* **Symptoms**: Asynchronous processing status remains `pending`.
* **Action**:
  ```bash
  docker compose restart worker
  docker compose logs worker --tail 50 -f
  ```

---

### 11. Disk Space Exhaustion Mitigation
* **Action**:
  ```bash
  # Prune orphaned MinIO objects and stale upload chunks
  docker compose exec -e PYTHONPATH=. backend python scripts/storage_integrity_audit.py --repair --confirm-repair
  # Clean old local backups
  python scripts/backup_manager.py
  # Remove unused Docker images
  docker image prune -f
  ```

---

### 12. TLS Certificate Renewal Failure
* **Action**:
  ```bash
  docker run --rm \
    -v /opt/cloudbox/certbot/www:/var/www/certbot \
    -v /opt/cloudbox/certbot/conf:/etc/letsencrypt \
    certbot/certbot renew --dry-run
  ```

---

### 13. Application Upgrade Procedure
* **Action**:
  ```bash
  bash scripts/deploy.sh
  ```

---

### 14. Application Rollback Procedure
* **Action**:
  ```bash
  bash scripts/rollback.sh
  ```

---

### 15. Monitoring & Alert Troubleshooting
* **Action**:
  ```bash
  # Check Prometheus scrape targets
  curl -s http://localhost:9090/api/v1/targets | jq .
  # Check Alertmanager alerts
  curl -s http://localhost:9093/api/v2/alerts | jq .
  ```
