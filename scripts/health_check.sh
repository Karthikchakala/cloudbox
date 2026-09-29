#!/usr/bin/env bash
# CloudBox Operational Health & Diagnostic Script

set -e

echo "========================================================================"
echo "  CLOUDBOX SYSTEM HEALTH & DIAGNOSTIC CHECK"
echo "  Timestamp: $(date -u +"%Y-%m-%dT%H:%M:%SZ")"
echo "========================================================================"

FAILED=0

check_endpoint() {
    local name="$1"
    local url="$2"
    echo -n "[*] Checking ${name} (${url})... "
    if curl -s -f -m 5 "${url}" > /dev/null; then
        echo "OK [✓]"
    else
        echo "FAILED [✗]"
        FAILED=$((FAILED + 1))
    fi
}

# 1. Check Reverse Proxy
check_endpoint "Nginx Reverse Proxy" "http://localhost/nginx_health"

# 2. Check Backend Health
check_endpoint "Backend API Health" "http://localhost/health"

# 3. Check Metrics Endpoint
check_endpoint "Prometheus Metrics" "http://localhost:5000/api/metrics/prometheus"

# 4. Check Container States
echo -n "[*] Checking Docker container states... "
RUNNING=$(docker compose ps --status running -q)
if [ -n "$RUNNING" ]; then
    echo "ALL RUNNING [✓]"
else
    echo "CONTAINERS NOT RUNNING [✗]"
    FAILED=$((FAILED + 1))
fi

echo "------------------------------------------------------------------------"
if [ $FAILED -eq 0 ]; then
    echo "[+] SYSTEM STATUS: ALL CHECKS PASSED [HEALTHY]"
    exit 0
else
    echo "[-] SYSTEM STATUS: ${FAILED} CHECKS FAILED [UNHEALTHY]"
    exit 1
fi
