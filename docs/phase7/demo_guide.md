# CloudBox Phase 7 — Comprehensive Practical Demonstration Guide

This guide provides step-by-step instructions, exact terminal commands, expected outputs, and talking points for presenting the Phase 7 CloudBox implementation.

---

## Demonstration Overview

| Demo | Title | Key Docker / SRE Concepts Demonstrated |
| :---: | :--- | :--- |
| **A** | Cloud Deployment | Production Compose, dual-bridge networking, health checks, multi-stage images |
| **B** | HTTPS & TLS | Reverse proxy SSL termination, security headers, HSTS, HTTP redirection |
| **C** | Off-Site Replication | Cryptographic backup bundling, S3 object API, SHA-256 sidecars, retention |
| **D** | Disaster Recovery | Pre-flight manifest verification, isolated recovery test, non-destructive validation |
| **E** | Prometheus & Grafana | Real-time metric scraping, time-series analysis, multi-tier Grafana dashboards |
| **F** | Controlled Failure Alert | Prometheus alert evaluation rules, Alertmanager state transitions, incident detection |
| **G** | Backup Failure & Retry | Bounded exponential backoff, fault tolerance, local artifact preservation |
| **H** | Deployment & Rollback | Automated pre-deploy backup, health check polling, automated rollback on failure |

---

### Demonstration A — Cloud Deployment
* **Action**: Launch CloudBox production stack and verify all services.
* **Commands**:
  ```bash
  docker compose -f compose.yaml -f compose.prod.yaml up -d
  docker compose ps
  bash scripts/health_check.sh
  ```
* **Expected Output**: All containers in `Up (healthy)` state. Output: `SYSTEM STATUS: ALL CHECKS PASSED [HEALTHY]`.
* **Talking Point**: CloudBox isolates public-facing frontend/Nginx from backend database/storage via two isolated Docker bridge networks (`frontend_net` and `backend_net`).

---

### Demonstration B — HTTPS Configuration
* **Action**: Verify Nginx SSL termination and security headers.
* **Commands**:
  ```bash
  curl -I http://localhost/health
  curl -k -I https://localhost/health
  ```
* **Expected Output**:
  ```text
  Strict-Transport-Security: max-age=31536000; includeSubDomains
  X-Content-Type-Options: nosniff
  X-Frame-Options: DENY
  ```
* **Talking Point**: Nginx terminates TLS using Let's Encrypt / modern TLS 1.3 ciphers, injecting security headers to protect against clickjacking and MIME-sniffing.

---

### Demonstration C — Off-Site Backup Replication
* **Action**: Generate unified backup and replicate to remote S3 storage.
* **Commands**:
  ```bash
  python scripts/backup_sync.py
  cat backups/backup_status.json
  ```
* **Expected Output**: Bundle created, master SHA-256 checksum calculated, replication status recorded.
* **Talking Point**: CloudBox creates consistent snapshots combining PostgreSQL database dumps and MinIO storage hierarchies with cryptographic manifest tracking.

---

### Demonstration D — Disaster Recovery Isolated Restore
* **Action**: Restore backup bundle into an isolated test database and bucket.
* **Commands**:
  ```bash
  python scripts/restore_manager.py --isolated
  ```
* **Expected Output**:
  ```text
  [*] 1/4 Verifying master bundle checksum...
      [+] Master checksum valid: 76f2fcf1707af292...
  [*] 2/4 Extracting & verifying manifest.json...
      [+] Database dump integrity verified.
      [+] All storage object checksums verified.
  [*] 3/4 Creating isolated test database 'cloudbox_db_test_dr'...
  [*] 3/4 Restoring PostgreSQL database into 'cloudbox_db_test_dr'...
  [*] 4/4 Restoring MinIO objects into 'cloudbox-uploads-test'...
  [+] ISOLATED TEST RESTORE VERIFIED: Data successfully restored to 'cloudbox_db_test_dr' and 'cloudbox-uploads-test'.
  ```
* **Talking Point**: Recovery is validated end-to-end without risking live production databases or object stores.

---

### Demonstration E — Prometheus & Grafana Monitoring
* **Action**: Start monitoring stack and query metrics.
* **Commands**:
  ```bash
  docker compose -f compose.yaml -f compose.monitoring.yaml up -d
  curl -s http://localhost:5000/api/metrics/prometheus | grep cloudbox_
  ```
* **Expected Output**:
  ```text
  cloudbox_uptime_seconds 842
  cloudbox_db_up 1
  cloudbox_redis_up 1
  cloudbox_cache_hit_ratio 0.85
  cloudbox_backup_latest_status 1
  ```
* **Talking Point**: Grafana provides pre-provisioned operational dashboards tracking application throughput, infrastructure resource consumption, and backup status.

---

### Demonstration F — Failure Detection & Alerting
* **Action**: Stop Redis and demonstrate monitoring detecting the state.
* **Commands**:
  ```bash
  docker compose stop redis
  curl -s http://localhost:5000/api/metrics/prometheus | grep cloudbox_redis_up
  docker compose start redis
  ```
* **Expected Output**: `cloudbox_redis_up 0` during outage; backend continues serving requests via direct DB fallback. Alert `RedisDisconnected` triggers in Prometheus.

---

### Demonstration G — Backup Failure & Safe Fallback
* **Action**: Demonstrate local backup preservation even if remote upload fails.
* **Commands**:
  ```bash
  python -c "from app.services.remote_backup_service import remote_backup_service; print(remote_backup_service.replicate_bundle('nonexistent.tar.gz'))"
  ```
* **Expected Output**: Structured error handling returning `success: false` while safeguarding local data.

---

### Demonstration H — Automated Deployment & Rollback
* **Action**: Execute automated deployment script and health verification.
* **Commands**:
  ```bash
  powershell -File scripts/deploy.ps1
  powershell -File scripts/health_check.ps1
  ```
* **Expected Output**: Pre-deployment backup generated, containers rebuilt, health checks passed.
* **Talking Point**: Zero-downtime deployment automation with automated rollback protection if smoke tests fail.
