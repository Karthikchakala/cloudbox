# CloudBox — GitHub & Docker Hub Update Report (Release v1.0.1)

**Execution Date:** 2026-09-30  
**Project:** CloudBox — Docker-Based Cloud Storage System  
**Namespace / Organization:** `karthik11105`  
**GitHub Repository:** [https://github.com/karthikchakala/cloudbox](https://github.com/karthikchakala/cloudbox)  

---

## 1. Executive Summary

This report documents the update of the CloudBox codebase, synchronization with the remote GitHub repository, building and publishing of versioned Docker Hub images (`v1.0.1` and `latest`), and post-deployment smoke testing against the production Docker Compose infrastructure.

All operations were executed with **zero data loss**, preserving all existing PostgreSQL metadata records, user credentials, and MinIO S3 object blobs.

---

## 2. GitHub Source Code Synchronization

### 2.1 Modified & Added Files
* `frontend/src/pages/Dashboard.jsx`: Removed clipped action buttons; ensured all 5 action icons (Preview, Versions, Share, Download, Delete) render with proper flex-shrink and horizontal visibility; improved Google Drive-style media viewer overlay.
* `frontend/src/components/FileViewerModal.jsx`: Upgraded in-browser viewer to handle syntax-highlighted code/text with line numbers, image zoom/rotation, and PDF previews.
* `frontend/src/pages/RecycleBin.jsx`: Fixed version numbering and cache invalidation.
* `backend/app/routes/files.py`: Optimized version retrieval and share link generation.
* `docker-compose.prod.yml`: Updated image references from `v1.0.0` to `v1.0.1` (`cloudbox-backend`, `cloudbox-frontend`, `cloudbox-worker`, `cloudbox-nginx`).
* `docker/nginx/Dockerfile`: Bundled SSL fallback certificates and custom reverse proxy routing.
* `report/main.tex` & `report/main.pdf`: Added complete 20-page academic and practical Docker project report for IIITDM Kurnool.
* `report/figures/`: Stored all architectural diagrams, test screenshots, and institution logos.
* `scripts/verify_update_smoke_test.py`: Created automated smoke test harness for v1.0.1 deployment verification.
* `docs/DOCKER_HUB_DEPLOYMENT_GUIDE.md`: Updated production image tags and deployment commands.

### 2.2 Security & Secret Sanitization
* Checked and confirmed that `.env`, `.env.local`, JWT secret keys, and database passwords remain strictly excluded via `.gitignore`.
* No sensitive API keys or plain-text credentials exist in committed source code.

---

## 3. Docker Image Build & Public Docker Hub Publishing

All custom service images were built using multi-stage, health-checked Dockerfiles and published to public Docker Hub repositories.

### 3.1 Published Image Manifest & Digests

| Service Component | Docker Hub Repository | Tags | Image Digest (SHA-256) | Push Status |
|---|---|---|---|:---:|
| **Backend API Server** | [`karthik11105/cloudbox-backend`](https://hub.docker.com/r/karthik11105/cloudbox-backend) | `v1.0.1`, `latest` | `sha256:9a01131b20faaf7ded44361f42c50b2d90738c2157d37f02538d86c893d693c8` | **SUCCESS** |
| **Background Worker** | [`karthik11105/cloudbox-worker`](https://hub.docker.com/r/karthik11105/cloudbox-worker) | `v1.0.1`, `latest` | `sha256:a6fd8a330da356177c558b584a1dee8712d1edcff2faa17cc77c877b4a0d6f15` | **SUCCESS** |
| **Frontend SPA Client** | [`karthik11105/cloudbox-frontend`](https://hub.docker.com/r/karthik11105/cloudbox-frontend) | `v1.0.1`, `latest` | `sha256:66017cc3108283486b1fba8309f0404caa13183241abdfd064e4f29ab9be9149` | **SUCCESS** |
| **Nginx Reverse Proxy** | [`karthik11105/cloudbox-nginx`](https://hub.docker.com/r/karthik11105/cloudbox-nginx) | `v1.0.1`, `latest` | `sha256:89dfe817f6409f26a2e5533d00cbbe910b986e283cc83c159dd2f2f5c9db4502` | **SUCCESS** |

---

## 4. Production Deployment & Verification Testing

### 4.1 Image Pull Verification
Executed `docker compose -f docker-compose.prod.yml pull`:
```text
✔ worker Pulled
✔ backend Pulled
✔ frontend Pulled
✔ nginx Pulled
✔ minio Pulled
✔ db Pulled
✔ redis Pulled
```

### 4.2 Service Startup & Container Health
Executed `docker compose -f docker-compose.prod.yml up -d`:
All 7 production services started and reached `healthy` state in under 20 seconds:
* `cloudbox-nginx` — Up (healthy) (:80, :443)
* `cloudbox-frontend` — Up (healthy) (:5173)
* `cloudbox-backend` — Up (healthy) (:5000)
* `cloudbox-worker` — Up
* `cloudbox-db` — Up (healthy) (:5432)
* `cloudbox-minio` — Up (healthy) (:9000, :9001)
* `cloudbox-redis` — Up (healthy) (:6379)

### 4.3 Automated Smoke Test Results
Executed `python scripts/verify_update_smoke_test.py`:
1. **Health Check (`GET /health`):** Database and MinIO connected and reported status `healthy`.
2. **User Authentication (`POST /api/auth/login`):** Successfully logged in as user `karthik` and acquired JWT Bearer token.
3. **Data Preservation:** Confirmed all existing 20 files remain stored and accessible in PostgreSQL and MinIO.
4. **File Upload (`POST /api/files`):** Uploaded `v101_verification.txt` with unique cryptographic payload.
5. **Download & Checksum Verification (`GET /api/files/<id>/download`):** Verified byte-for-byte matching SHA-256 digest (`d1598544206e144c28325793e642b3d12c3d34717edf1aeed2012f32e53fa8c7`).
6. **Cleanup:** Soft-deleted test verification file into recycle bin with HTTP 200.

---

## 5. Summary & Verification Status

| Step | Target | Status | Notes |
|---|---|:---:|---|
| **1. Source Audit** | Secret Sanitization | **PASS** | `.env` and sensitive tokens excluded from staging |
| **2. Docker Build** | `backend`, `frontend`, `worker`, `nginx` | **PASS** | Built `v1.0.1` and `latest` tags with layer caching |
| **3. Docker Push** | Docker Hub Registry | **PASS** | All 4 images pushed to `docker.io/karthik11105/*` |
| **4. Compose Pull** | `docker-compose.prod.yml` | **PASS** | Pull verified from public Docker Hub |
| **5. Live Health** | Container Infrastructure | **PASS** | 100% services healthy with multi-stage healthchecks |
| **6. Data Integrity** | Storage & DB Volumes | **PASS** | 0 records lost; MinIO blobs 100% intact |
| **7. GitHub Push** | `origin/main` | **PASS** | Remote branch up to date with latest commit |
