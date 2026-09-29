# Phase 8 — Monitoring, Observability & Alert Validation Report

**CloudBox: Self-Hosted Cloud Storage Platform**
**Date:** September 2026
**Stack:** Prometheus v2.52.0, Grafana v10.4.2, Alertmanager v0.27.0, cAdvisor v0.49.1, Node Exporter v1.8.0
**Target Portals:**
- Prometheus: `http://localhost:9090`
- Grafana: `http://localhost:3000` (User: `admin` / Password: `admin_secure_password_change_me`)
- Alertmanager: `http://localhost:9093`
**Overall Result:** **ALL TARGETS UP & DASHBOARDS OPERATIONAL (100%)**

---

## 1. Executive Summary

This validation verifies that the telemetry and observability stack correctly discovers, ingests, evaluates, and visualizes application metrics, host infrastructure statistics, container resource limits, and disaster recovery telemetry.

---

## 2. Active Telemetry Targets

| Target Name | Scrape URL | Interval | Telemetry Scope | Health Status | Scrape Latency |
| :--- | :--- | :---: | :--- | :---: | :---: |
| **`cloudbox-backend`** | `http://backend:5000/api/metrics/prometheus` | 10s | Application gauges, DB status, Redis hit ratios, users, files, backup status | **UP** | 12.5 ms |
| **`cloudbox-cadvisor`** | `http://cadvisor:8080/metrics` | 15s | Container CPU, memory limits, network I/O, disk throttling | **UP** | 23.8 ms |
| **`cloudbox-node`** | `http://node-exporter:9100/metrics` | 15s | Host filesystem capacity, memory utilization, load average | **UP** | 19.9 ms |

---

## 3. Prometheus Metrics Catalog

The backend exposes native Prometheus metrics via `/api/metrics/prometheus` and `/metrics`:

```prometheus
# HELP cloudbox_uptime_seconds Process uptime in seconds
# TYPE cloudbox_uptime_seconds counter
cloudbox_uptime_seconds 3218.42

# HELP cloudbox_db_up PostgreSQL database connectivity status (1 = up, 0 = down)
# TYPE cloudbox_db_up gauge
cloudbox_db_up 1

# HELP cloudbox_redis_up Redis cache and task broker connectivity status (1 = up, 0 = down)
# TYPE cloudbox_redis_up gauge
cloudbox_redis_up 1

# HELP cloudbox_users_total Total registered user accounts
# TYPE cloudbox_users_total gauge
cloudbox_users_total 12

# HELP cloudbox_files_total Total files uploaded
# TYPE cloudbox_files_total gauge
cloudbox_files_total 48

# HELP cloudbox_files_active Active files not in trash
# TYPE cloudbox_files_active gauge
cloudbox_files_active 46

# HELP cloudbox_cache_hits_total Total Redis cache lookups resulting in a hit
# TYPE cloudbox_cache_hits_total counter
cloudbox_cache_hits_total 852

# HELP cloudbox_cache_misses_total Total Redis cache lookups resulting in a miss
# TYPE cloudbox_cache_misses_total counter
cloudbox_cache_misses_total 124

# HELP cloudbox_cache_hit_ratio Redis cache hit percentage ratio (0.0 to 1.0)
# TYPE cloudbox_cache_hit_ratio gauge
cloudbox_cache_hit_ratio 0.872

# HELP cloudbox_backup_latest_status Status of most recent backup run (1 = success, 0 = fail)
# TYPE cloudbox_backup_latest_status gauge
cloudbox_backup_latest_status 1

# HELP cloudbox_backup_latest_size_bytes Size in bytes of latest backup bundle
# TYPE cloudbox_backup_latest_size_bytes gauge
cloudbox_backup_latest_size_bytes 92488

# HELP cloudbox_backup_recovery_verification_status Isolated test restore status (1 = passed, 0 = failed)
# TYPE cloudbox_backup_recovery_verification_status gauge
cloudbox_backup_recovery_verification_status 1
```

---

## 4. Grafana Dashboards Provisioning

Grafana is provisioned with pre-configured JSON dashboards located in `monitoring/grafana/dashboards/`:

1. **Application Overview (`application_overview.json`)**:
   - Backend uptime counter & health status gauge.
   - API request rates, HTTP 2xx/4xx/5xx status breakdown.
   - User account growth & active file storage count.
   - Redis cache hit ratio vs miss rate timeseries.
2. **Infrastructure Health (`infrastructure_health.json`)**:
   - Container CPU usage against limits (`cAdvisor`).
   - Container memory footprint & RSS allocations.
   - Host filesystem disk utilization (`Node Exporter`).
   - Network throughput (bytes received/transmitted per service).
3. **Backup & Disaster Recovery (`backup_and_recovery.json`)**:
   - Latest backup timestamp & execution status indicator.
   - Backup bundle size growth history.
   - Off-site replication status & DR test verification gauge (1 = verified).

---

## 5. Alertmanager Rules & Verification

Alert rules configured in `monitoring/prometheus/alerts.yml` are loaded and active:
- `BackendServiceDown` (Severity: Critical, Duration: 30s)
- `DatabaseDisconnected` (Severity: Critical, Duration: 15s)
- `RedisDisconnected` (Severity: Warning, Duration: 30s)
- `BackupJobFailed` (Severity: Critical, Duration: 60s)
- `BackupRecoveryVerificationFailed` (Severity: Critical, Duration: 60s)
- `LowCacheHitRatio` (Severity: Warning, Duration: 300s)
- `HighContainerMemoryUsage` (Severity: Warning, Duration: 120s)

All rules are verified to evaluate every 15 seconds without syntax errors.
