# CloudBox Phase 8 — Master Practical Demonstration Guide

**Project:** CloudBox — Enterprise Mini Cloud Storage Platform
**Target Audience:** Evaluator / Professor / Cloud Architecture Review Committee
**Presenter Role:** Senior DevOps Engineer & Cloud Architect
**Prerequisites:** Docker Engine / Docker Desktop running, Terminal / PowerShell

---

## Demonstration Overview Matrix

| Demo | Title | Key Concepts Demonstrated | Duration |
| :---: | :--- | :--- | :---: |
| **Demo 1** | **System Architecture & Orchestration** | Multi-tier Docker Compose, Network Isolation (`frontend_net`, `backend_net`), Persistent Volumes | 3 min |
| **Demo 2** | **End-to-End File Lifecycle & Hash Integrity** | Upload, MinIO S3 Binary Storage, SHA-256 Hashing, Metadata in PostgreSQL, Soft Delete & Restore | 4 min |
| **Demo 3** | **Network Boundaries & Ingress Security** | Nginx Reverse Proxy, Security Headers, Rate Limiting, ACME TLS Routing, Internal Service Isolation | 3 min |
| **Demo 4** | **Volume Persistence & Zero Data Loss** | Data retention across container restarts, named volume mechanics | 3 min |
| **Demo 5** | **Cryptographic Backup & Isolated DR Restore** | Atomic backup creation, SHA-256 Manifest verification, Isolated non-destructive test restore | 4 min |
| **Demo 6** | **Prometheus & Grafana Observability** | Live metrics scraping, 3 provisioned Grafana dashboards, Alertmanager rule evaluation | 3 min |
| **Demo 7** | **Failure Injection & High Availability** | Live service crash simulation (Redis outage), graceful DB fallback, zero-downtime recovery | 4 min |

---

## 🖥️ Demo 1: System Architecture & Orchestration

### Objective
Demonstrate how the 11 CloudBox containers are orchestrated across isolated networks and persistent volumes.

### Commands to Run
```powershell
docker compose -f compose.yaml -f compose.monitoring.yaml ps
docker network ls | grep -E "frontend_net|backend_net"
docker volume ls | grep -E "postgres_data|minio_data|redis_data"
```

### Expected Output
```text
NAME                     IMAGE                       STATUS                   PORTS
cloudbox-nginx           cloudbox-nginx              Up (healthy)             0.0.0.0:80->80/tcp, 0.0.0.0:443->443/tcp
cloudbox-frontend        cloudbox-frontend           Up (healthy)             0.0.0.0:5173->5173/tcp
cloudbox-backend         cloudbox-backend            Up (healthy)             0.0.0.0:5000->5000/tcp
cloudbox-worker          cloudbox-backend            Up                       5000/tcp
cloudbox-redis           redis:7-alpine              Up (healthy)             6379/tcp
cloudbox-db              postgres:16-alpine          Up (healthy)             5432/tcp
cloudbox-minio           minio/minio:RELEASE...      Up (healthy)             0.0.0.0:9000-9001->9000-9001/tcp
cloudbox-prometheus      prom/prometheus:v2.52.0     Up                       0.0.0.0:9090->9090/tcp
cloudbox-grafana         grafana/grafana:10.4.2      Up                       0.0.0.0:3000->3000/tcp
cloudbox-alertmanager    prom/alertmanager:v0.27.0   Up                       0.0.0.0:9093->9093/tcp
cloudbox-cadvisor        gcr.io/cadvisor/cadvisor    Up (healthy)             8080/tcp
cloudbox-node-exporter   prom/node-exporter:v1.8.0   Up                       9100/tcp
```

### What to Explain
- **Network Segmentation**: Show that PostgreSQL, Redis, and internal communication are isolated on `backend_net`. External traffic is only permitted via Nginx (`frontend_net`).
- **Data Durability**: Point out `postgres_data`, `minio_data`, and `redis_data` ensuring no data loss when containers are rebuilt.

---

## 📁 Demo 2: File Lifecycle & Cryptographic Integrity

### Objective
Show real-time file upload, cryptographic SHA-256 hashing, storage in MinIO, metadata persistence in PostgreSQL, and download integrity.

### Commands to Run
```powershell
# Run the automated End-to-End lifecycle validator
python scripts/e2e_functional_test.py
```

### Expected Output
```text
============================================================
 CloudBox Phase 8 - End-to-End Functional Validation Suite
============================================================
[1] Authentication & Access Control Tests
  [PASS] 1.1 Register User A Status: 201
  [PASS] 1.3 Login User A & JWT Issuance Token acquired
[2] File Management & Storage Integrity Tests
  [PASS] 2.1 File Upload File ID: 6da9ee78-0efe...
  [PASS] 2.3 File Download & SHA-256 Checksum Match Checksum: 96eb0adc...
[3] File Versioning Tests
  [PASS] 3.1 Upload File Version 2 Status: 201
  [PASS] 3.3 Restore Historical Version 1 Status: 200
[4] Sharing Links & Access Permissions Tests
  [PASS] 4.1 Create Public Share Link Token: 6cDkDsFZ...
[5] Recycle Bin & Soft Delete Lifecycle Tests
  [PASS] 5.1 Move File to Recycle Bin Status: 200
  [PASS] 5.4 Restore File from Recycle Bin Status: 200
[6] Resumable Chunked Multi-Part Upload Tests
  [PASS] 6.3 Complete & Reassemble Chunked Upload Created File ID: 1fd5ee4c...
  [PASS] 6.4 Verify Reassembled Checksum Integrity Size: 275000 bytes, Checksum Match: True
============================================================
E2E VALIDATION SUMMARY: 26/26 PASSED (100.0%)
============================================================
```

### What to Explain
- **Hashing**: Every byte uploaded is hashed with SHA-256 in memory as it streams into MinIO S3 object storage.
- **Resumable Chunking**: Multi-part chunk uploads allow large files to upload reliably over unstable connections.

---

## 🛡️ Demo 3: Networking & Ingress Security

### Objective
Demonstrate Nginx reverse proxy routing, rate limiting, and health probes.

### Commands to Run
```powershell
# Test Nginx proxy health
curl.exe -i http://localhost/nginx_health

# Test Backend API health through reverse proxy
curl.exe -i http://localhost/health
```

### Expected Output
```http
HTTP/1.1 200 OK
Server: nginx
Content-Type: application/json
X-Content-Type-Options: nosniff
X-Frame-Options: DENY
Referrer-Policy: strict-origin-when-cross-origin

{"status":"healthy","service":"cloudbox-backend",...}
```

### What to Explain
- Point out security headers (`X-Frame-Options: DENY`, `nosniff`, `Content-Security-Policy`).
- Explain rate-limiting zones protecting `/api/auth/` from credential stuffing.

---

## 💾 Demo 4: Data Persistence Across Restarts

### Objective
Demonstrate that restarting services does not destroy database rows or uploaded files.

### Commands to Run
```powershell
# Restart the database and MinIO storage containers
docker compose restart db minio

# Run health check probe to confirm data persistence and cluster health
powershell -File scripts/health_check.ps1
```

### Expected Output
```text
========================================================================
  CLOUDBOX SYSTEM HEALTH & DIAGNOSTIC CHECK
========================================================================
[*] Checking Nginx Reverse Proxy (http://localhost/nginx_health)... OK [PASS]
[*] Checking Backend API Health (http://localhost/health)... OK [PASS]
[*] Checking Prometheus Metrics (http://localhost:5000/api/metrics/prometheus)... OK [PASS]
[*] Checking Docker container states... ALL RUNNING [PASS]
------------------------------------------------------------------------
[+] SYSTEM STATUS: ALL CHECKS PASSED [HEALTHY]
```

---

## 🔄 Demo 5: Cryptographic Backup & Isolated DR Restore

### Objective
Demonstrate the execution of an atomic backup bundle with SHA-256 manifest verification and an automated isolated restoration into a test database.

### Commands to Run
```powershell
python scripts/backup_sync.py --verify-recovery
```

### Expected Output
```text
===========================================================================
  CLOUDBOX AUTOMATED BACKUP, SYNC & DISASTER RECOVERY PIPELINE
===========================================================================
[*] STEP 1: Generating local cryptographic backup bundle...
    [+] DB Dump: 72340 bytes | SHA-256 verified
    [+] Objects Archived: 101 files (32.3 MB)
    [+] Packaging & compressing bundle tarball...
    [+] Master SHA-256: a0427b8e7d1dceb7...
[*] STEP 2: Replicating backup bundle to offsite object storage...
    [+] Replication status: LOCAL_ONLY (Verified)
[*] STEP 3: Executing Automated Isolated Recovery Verification...
    [+] Master checksum valid.
    [+] Database dump integrity verified.
    [+] All storage object checksums verified.
    [+] Restoring PostgreSQL database into 'cloudbox_db_test_dr'...
    [+] Restoring MinIO objects into 'cloudbox-uploads-test'...
    [+] Cleaned up temporary test database.
    [+] Recovery verification result: PASSED [OK]
===========================================================================
  BACKUP PIPELINE COMPLETE: SUCCESS [OK]
===========================================================================
```

### What to Explain
- Highlight that the restore runs in an isolated database sandbox (`cloudbox_db_test_dr`), proving backups work without corrupting production data.

---

## 📊 Demo 6: Prometheus & Grafana Observability

### Objective
Show live telemetry collection, pre-provisioned Grafana dashboards, and active Alertmanager rules.

### Action Steps
1. Open Grafana in your browser: [http://localhost:3000](http://localhost:3000)
2. Log in with:
   - **Username:** `admin`
   - **Password:** `admin_secure_password_change_me`
3. Navigate to **Dashboards** and show:
   - **Application Overview**: Backend uptime, request count, cache hit ratio.
   - **Infrastructure Health**: CPU/Memory utilization from cAdvisor and Node Exporter.
   - **Backup & Disaster Recovery**: Backup status indicators and size growth charts.
4. Open Prometheus UI: [http://localhost:9090/targets](http://localhost:9090/targets) to show all 3 targets in `UP` state.

---

## ⚡ Demo 7: Failure Injection & High Availability

### Objective
Simulate a live Redis outage to demonstrate that the application gracefully falls back to direct database lookups without downtime.

### Commands to Run
```powershell
# Run the automated resilience test harness
python scripts/resilience_test_harness.py
```

### Expected Output
```text
==========================================================================================
  CLOUDBOX RESILIENCE & FAILURE-INJECTION TEST HARNESS
==========================================================================================
[*] Scenario 1: Testing Backend Service Restart...
  [PASS] 1. Backend Service Restart               | RTO:  7.95s | Backend cleanly re-attached
[*] Scenario 2: Testing Worker Service Restart...
  [PASS] 2. Celery Worker Restart                 | RTO:  0.03s | Worker resumed queue loop
[*] Scenario 3: Simulating Redis Outage (Testing Cache Fallback)...
  [PASS] 3. Redis Outage & Fallback               | RTO:  0.01s | API operated in fallback mode
[*] Scenario 4: Testing PostgreSQL Container Restart...
  [PASS] 4. PostgreSQL Database Restart           | RTO:  0.03s | DB pool reconnected
[*] Scenario 5: Testing MinIO Object Storage Restart...
  [PASS] 5. MinIO Storage Restart                 | RTO:  0.01s | S3 client reconnected
[*] Scenario 6: Testing Nginx Reverse Proxy Restart...
  [PASS] 6. Nginx Reverse Proxy Restart           | RTO:  0.03s | Routing restored
[*] Verifying post-resilience system integrity via E2E functional test...
  [PASS] 7. Post-Fault Data Integrity             | RTO:  0.00s | All 26 E2E tests passed
==========================================================================================
                               RESILIENCE TEST SUMMARY
==========================================================================================
Passed: 7/7 (100.0%)
==========================================================================================
```

### What to Explain
- Highlight the measured Recovery Time Objective (RTO) under 8 seconds for all scenarios.
- Conclude that CloudBox achieves high availability, comprehensive observability, and reliable disaster recovery.
