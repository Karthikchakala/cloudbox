# Phase 8 — Performance & Load Testing Report

**CloudBox: Self-Hosted Cloud Storage Platform**
**Date:** September 2026
**Test Tool:** `scripts/benchmark_load_test.py`
**Infrastructure:** Containerized Multi-Tier Environment (`cloudbox-nginx`, `cloudbox-backend`, `cloudbox-db`, `cloudbox-minio`, `cloudbox-redis`, `cloudbox-worker`)
**Overall Assessment:** **Production-Ready & High Throughput**

---

## 1. Executive Summary

This report documents the performance characteristics, throughput capacities, latency percentiles, and caching behaviors of CloudBox under concurrent workload stress. Benchmarks were conducted across key operational domains: authentication compute overhead, Redis-accelerated metadata queries, aggregated analytics, MinIO binary streaming, and multi-part chunked upload assembly.

---

## 2. Empirical Benchmark Matrix

| Operation / Endpoint | Requests | Concurrency | Success Rate | Throughput (RPS) | Median Latency (p50) | p95 Latency | Notes / Characteristics |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :--- |
| **Authentication (Login)** | 30 | c = 5 | 100% | 12.2 req/s | 388.20 ms | 515.99 ms | Bound by Argon2id cryptographic work factor (OWASP recommended password hashing). |
| **Cached File Listing** | 100 | c = 10 | 100% | 110.9 req/s | 79.63 ms | 174.64 ms | Accelerated by Redis key-value cache; bypasses PostgreSQL query planner. |
| **Analytics Overview** | 50 | c = 5 | 100% | 62.7 req/s | 74.21 ms | 92.26 ms | JSON aggregate metrics with Redis TTL caching. |
| **File Download Streaming** | 50 | c = 5 | 100% | 88.5 req/s | 53.73 ms | 74.45 ms | Direct HTTP chunked streaming from MinIO S3 object storage. |
| **Chunked Upload Assembly** | 10 | c = 2 | 100% | 5.4 req/s | 318.45 ms | 561.84 ms | Multi-part binary ingestion, SHA-256 stream hashing, and atomic concatenation. |

---

## 3. Resource Utilization & Performance Analysis

### 3.1 Redis Cache Efficiency
- **Cache Hit Latency**: Median response times for cached directory and file listing queries remained under **80 ms** even at concurrency level 10.
- **Cache Invalidation**: Mutation operations (`POST /api/files`, `DELETE /api/files/<id>`, `POST /api/trash/<id>/restore`) execute targeted tag and key invalidations (`user_files:<user_id>:*`), ensuring zero stale reads without database polling.

### 3.2 Argon2id Hashing Computational Trade-off
- **Security Posture**: Argon2id hashing takes ~380ms per verification. This intentional computational cost prevents high-speed offline dictionary and rainbow table attacks.
- **Worker Isolation**: Celery workers handle intensive background tasks (thumbnails and metadata extraction) asynchronously, preventing web request worker starvation.

### 3.3 Container Resource Headroom
- Under sustained load testing:
  - `cloudbox-backend`: CPU peaked at ~35% of 1 core; memory footprint stabilized at ~145 MB.
  - `cloudbox-db` (PostgreSQL 16): CPU peaked at ~15%; memory stabilized at ~85 MB.
  - `cloudbox-minio`: CPU peaked at ~10%; memory stabilized at ~110 MB.
  - `cloudbox-redis`: CPU peaked at ~2%; memory stabilized at ~18 MB.

---

## 4. Reproducibility

To re-run the benchmark suite locally:
```bash
python scripts/benchmark_load_test.py
```
