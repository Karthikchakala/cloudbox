#!/usr/bin/env bash
# CloudBox Automated Production Deployment Script

set -e

echo "========================================================================"
echo "  CLOUDBOX AUTOMATED DEPLOYMENT WORKFLOW"
echo "  Timestamp: $(date -u +"%Y-%m-%dT%H:%M:%SZ")"
echo "========================================================================"

# 1. Verify Configuration & Environment
echo "[*] STEP 1: Validating environment and configuration..."
if [ ! -f .env ]; then
    echo "[-] Error: .env file missing! Copy .env.example and configure production credentials." >&2
    exit 1
fi

# 2. Pre-Deployment Safety Backup
echo "[*] STEP 2: Creating pre-deployment safety backup..."
python3 scripts/backup_manager.py || {
    echo "[-] Pre-deployment backup failed! Aborting deployment." >&2
    exit 1
}

# 3. Pull & Build Container Images
echo "[*] STEP 3: Building container images..."
docker compose -f compose.yaml -f compose.prod.yaml build

# 4. Controlled Deployment
echo "[*] STEP 4: Deploying services in controlled order..."
docker compose -f compose.yaml -f compose.prod.yaml up -d

# 5. Await Health Checks
echo "[*] STEP 5: Waiting for container health checks..."
MAX_WAIT=60
WAITED=0
until bash scripts/health_check.sh > /dev/null 2>&1 || [ $WAITED -ge $MAX_WAIT ]; do
    sleep 3
    WAITED=$((WAITED + 3))
    echo "    Waiting for services (${WAITED}s/${MAX_WAIT}s)..."
done

# 6. Post-Deployment Verification
echo "[*] STEP 6: Executing post-deployment smoke tests..."
if bash scripts/health_check.sh; then
    echo "========================================================================"
    echo "  [+] DEPLOYMENT COMPLETED SUCCESSFULLY"
    echo "========================================================================"
    exit 0
else
    echo "[-] Deployment failed smoke tests! Triggering rollback..." >&2
    bash scripts/rollback.sh
    exit 1
fi
