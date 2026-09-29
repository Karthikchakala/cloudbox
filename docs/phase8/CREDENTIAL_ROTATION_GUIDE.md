# CloudBox — Enterprise Credential Rotation & Secret Management Runbook

**Project:** CloudBox — Self-Hosted Cloud Storage Platform
**Audience:** DevOps Engineers, Security Administrators & Site Reliability Engineers
**Date:** September 2026

---

## 1. Overview & Security Rules

This runbook outlines the standard operating procedures for rotating service passwords, encryption keys, and administrative secrets in CloudBox without service degradation or volume corruption.

### ⚠️ Mandatory Security Rules
1. **Never delete named volumes**: Do not run `docker compose down -v` during password rotations.
2. **Synchronize Clients & Servers**: Always update client configuration (`backend`, `worker`) simultaneously with service containers (`redis`, `db`, `minio`).
3. **Audit Redaction**: Ensure rotated secrets are never logged in plaintext or committed to Git.

---

## 2. Generating Cryptographic Secrets (PowerShell Workflow)

Generate high-entropy 256-bit hexadecimal or URL-safe secrets:

```powershell
# Generate a 32-byte cryptographic hex secret
$SecretKey = -join ((1..32) | ForEach-Object { '{0:x2}' -f (Get-Random -Minimum 0 -Maximum 256) })
Write-Host "Generated Secret: $SecretKey"

# Or using Python in terminal
python scripts/generate_secret.py
```

---

## 3. Step-by-Step Rotation Procedures

### Procedure A: Rotating Redis Password (`REDIS_PASSWORD`)

1. **Update `.env`**:
   ```env
   REDIS_PASSWORD=YourNewStrongRedisPassword123!
   ```
2. **Apply Configuration to Containers**:
   ```powershell
   docker compose up -d --force-recreate redis backend worker
   ```
3. **Verify Redis Authentication**:
   ```powershell
   $env:REDISCLI_AUTH = "YourNewStrongRedisPassword123!"
   docker compose exec -e REDISCLI_AUTH=$env:REDISCLI_AUTH redis redis-cli ping
   Remove-Item Env:REDISCLI_AUTH
   
   docker compose exec backend python -c "from app.services.cache_service import cache_service; print(cache_service.is_available)"
   ```

---

### Procedure B: Rotating PostgreSQL Password (`POSTGRES_PASSWORD`)

Since PostgreSQL stores user hashes in its persistent data directory (`postgres_data`), rotating the password requires updating the running database engine before updating `.env`:

1. **Update Password inside PostgreSQL**:
   ```powershell
   docker compose exec db psql -U cloudbox_user -d cloudbox_db -c "ALTER USER cloudbox_user WITH PASSWORD 'NewStrongPostgresPass123!';"
   ```
2. **Update `.env`**:
   ```env
   POSTGRES_PASSWORD=NewStrongPostgresPass123!
   ```
3. **Recreate Dependent Services**:
   ```powershell
   docker compose up -d --force-recreate backend worker
   ```
4. **Verify Database Connectivity**:
   ```powershell
   docker compose exec backend python -c "from app.extensions import db; print(db.session.execute(db.text('SELECT 1')).scalar())"
   ```

---

### Procedure C: Rotating MinIO Root Password (`MINIO_ROOT_PASSWORD`)

1. **Update `.env`**:
   ```env
   MINIO_ROOT_PASSWORD=NewStrongMinioSecretKey123!
   ```
2. **Recreate MinIO, Backend & Worker**:
   ```powershell
   docker compose up -d --force-recreate minio backend worker
   ```
3. **Verify MinIO S3 API Handshake**:
   ```powershell
   docker compose exec backend python -c "from app.services.storage_service import storage_service; print(storage_service.client.list_buckets())"
   ```

---

### Procedure D: Rotating Grafana Admin Password (`GRAFANA_ADMIN_PASSWORD`)

1. **Update Password via Grafana CLI**:
   ```powershell
   docker compose exec cloudbox-grafana grafana-cli admin reset-admin-password "NewGrafanaAdminPassword123!"
   ```
2. **Update `.env`**:
   ```env
   GRAFANA_ADMIN_PASSWORD=NewGrafanaAdminPassword123!
   ```
3. **Verify Grafana API Login**:
   ```powershell
   curl.exe -s -u "admin:NewGrafanaAdminPassword123!" http://localhost:3000/api/users
   ```

---

### Procedure E: Rotating JWT Secret Key (`JWT_SECRET_KEY`)

> **Note:** Rotating `JWT_SECRET_KEY` will invalidate existing active user sessions, requiring users to log in again.

1. **Generate New Key & Update `.env`**:
   ```env
   JWT_SECRET_KEY=336f4a1c52c4471aae0a539f9d503e6b844a648ad6c3ad1c57394257c8f1286c
   ```
2. **Recreate Backend**:
   ```powershell
   docker compose up -d --force-recreate backend
   ```
3. **Verify Login Flow**:
   ```powershell
   python scripts/e2e_functional_test.py
   ```
