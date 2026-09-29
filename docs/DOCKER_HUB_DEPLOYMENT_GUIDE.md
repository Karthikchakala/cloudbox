# CloudBox — Production Docker Hub Deployment Guide

This guide walks you through deploying CloudBox on another laptop, server, or cloud VM using the official, pre-built public Docker Hub images.

---

## 1. Prerequisites

Ensure the following tools are installed on the host machine:
* **Docker Engine** (v24.0+) or **Docker Desktop**
* **Docker Compose** (v2.20+)
* **Git** (to clone the configuration repository)

---

## 2. Deployment Architecture & Published Images

CloudBox images are published publicly to Docker Hub under the `karthik11105` namespace:

| Service | Docker Hub Image | Function |
|---|---|---|
| **Backend API** | `karthik11105/cloudbox-backend:v1.0.0` | Python Flask REST APIs, WSGI Gunicorn, Auth & Storage Engine |
| **Background Worker** | `karthik11105/cloudbox-worker:v1.0.0` | Celery asynchronous worker for uploads, backups, metadata processing |
| **Frontend SPA** | `karthik11105/cloudbox-frontend:v1.0.0` | React / Vite SPA with Google Drive-style media viewer |
| **Reverse Proxy** | `nginx:1.27-alpine` | SSL termination, rate-limiting, CSP headers, reverse proxy |
| **Database** | `postgres:16-alpine` | Relational database for users, file metadata, permissions, trash |
| **Object Storage** | `cgr.dev/chainguard/minio:latest` | S3-compatible high-performance object store |
| **Cache & Broker** | `redis:7-alpine` | In-memory cache & Celery task broker |

---

## 3. Step-by-Step Installation

### Step 1: Clone the Repository
```bash
git clone https://github.com/karthikchakala/cloudbox.git
cd cloudbox
```

### Step 2: Configure Environment Variables
Copy the configuration template:
```bash
cp .env.example .env
```

Open `.env` in your text editor and configure your production credentials:
```ini
# Generate unique 64-character secret keys:
# openssl rand -hex 32
SECRET_KEY=your_generated_secret_key_here
JWT_SECRET_KEY=your_generated_jwt_secret_key_here

# Service Passwords
POSTGRES_PASSWORD=your_secure_db_password
MINIO_ROOT_PASSWORD=your_secure_minio_password
REDIS_PASSWORD=your_secure_redis_password

# Ports (Default: 80, 443, 9000, 9001)
HTTP_PORT=80
HTTPS_PORT=443
MINIO_API_PORT=9000
MINIO_CONSOLE_PORT=9001
```

### Step 3: Pull the Published Images
Pull the pre-built images directly from Docker Hub without needing any local build toolchains:
```bash
docker compose -f docker-compose.prod.yml pull
```

### Step 4: Start the CloudBox Stack
Launch all services in detached mode:
```bash
docker compose -f docker-compose.prod.yml up -d
```

### Step 5: Verify Service Health
Check that all containers are healthy and running:
```bash
docker compose -f docker-compose.prod.yml ps
```

Expected healthy output:
```text
NAME                IMAGE                                    STATUS
cloudbox-backend    karthik11105/cloudbox-backend:v1.0.0     Up (healthy)
cloudbox-worker     karthik11105/cloudbox-worker:v1.0.0      Up
cloudbox-frontend   karthik11105/cloudbox-frontend:v1.0.0    Up (healthy)
cloudbox-nginx      nginx:1.27-alpine                        Up (healthy)
cloudbox-db         postgres:16-alpine                       Up (healthy)
cloudbox-minio      cgr.dev/chainguard/minio:latest          Up (healthy)
cloudbox-redis      redis:7-alpine                           Up (healthy)
```

---

## 4. Accessing the Application

Open your browser and navigate to:

| Application | URL | Initial Access |
|---|---|---|
| **CloudBox Web Interface** | `http://localhost` | Register a new administrator account or use configured credentials |
| **MinIO Storage Console** | `http://localhost:9001` | Username: `cloudbox_admin`<br>Password: `${MINIO_ROOT_PASSWORD}` |

---

## 5. Operations & Lifecycle Management

### Viewing Live Logs
```bash
# View all logs
docker compose -f docker-compose.prod.yml logs -f

# View backend logs specifically
docker compose -f docker-compose.prod.yml logs -f backend
```

### Stopping the Application (Preserving Data)
To stop the application while keeping your database, MinIO objects, and Redis volumes safe:
```bash
docker compose -f docker-compose.prod.yml down
```
> ⚠️ **CAUTION:** Never append `-v` unless you explicitly want to permanently delete all uploaded user files and database records.

### Upgrading to a New Version
When a new version (e.g. `v1.1.0`) is published:
1. Update image tags in `docker-compose.prod.yml`.
2. Pull the new images:
   ```bash
   docker compose -f docker-compose.prod.yml pull
   ```
3. Restart containers with zero-downtime recreation:
   ```bash
   docker compose -f docker-compose.prod.yml up -d
   ```

---

## 6. Security Checklist for Production

1. **Change Default Passwords:** Always change `password123` in `.env` to unique credentials before exposing ports.
2. **Enable HTTPS / SSL:** Update `deploy/nginx/default.conf` and mount your SSL certificates or configure Let's Encrypt Certbot.
3. **Firewall Rules:** In a multi-server setup, do not expose PostgreSQL (`5432`) or Redis (`6379`) to the public internet; keep them within the Docker internal bridge networks.
