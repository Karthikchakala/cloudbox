#!/usr/bin/env bash
# CloudBox Safe Rollback Script

set -e

echo "========================================================================"
echo "  CLOUDBOX SAFE APPLICATION ROLLBACK"
echo "  Timestamp: $(date -u +"%Y-%m-%dT%H:%M:%SZ")"
echo "========================================================================"

echo "[*] Restarting stable service stack..."
docker compose -f compose.yaml -f compose.prod.yaml restart backend frontend nginx worker

echo "[*] Checking service health after rollback..."
sleep 5
bash scripts/health_check.sh
echo "[+] Rollback completed. Stable state restored."
