# CloudBox Automated Production Deployment Script (PowerShell)

Write-Host "========================================================================" -ForegroundColor Cyan
Write-Host "  CLOUDBOX AUTOMATED DEPLOYMENT WORKFLOW" -ForegroundColor Cyan
Write-Host "  Timestamp: $(Get-Date -Format 'yyyy-MM-ddTHH:mm:ssZ')" -ForegroundColor Cyan
Write-Host "========================================================================" -ForegroundColor Cyan

# 1. Verify Configuration & Environment
Write-Host "[*] STEP 1: Validating environment and configuration..."
if (-not (Test-Path ".env")) {
    Write-Error "[-] Error: .env file missing! Copy .env.example and configure production credentials."
    exit 1
}

# 2. Pre-Deployment Safety Backup
Write-Host "[*] STEP 2: Creating pre-deployment safety backup..."
python scripts/backup_manager.py
if ($LASTEXITCODE -ne 0) {
    Write-Error "[-] Pre-deployment backup failed! Aborting deployment."
    exit 1
}

# 3. Pull & Build Container Images
Write-Host "[*] STEP 3: Building container images..."
docker compose -f compose.yaml -f compose.prod.yaml build

# 4. Controlled Deployment
Write-Host "[*] STEP 4: Deploying services in controlled order..."
docker compose -f compose.yaml -f compose.prod.yaml up -d

# 5. Await Health Checks & Verify
Write-Host "[*] STEP 5: Waiting for container health checks..."
Start-Sleep -Seconds 5
powershell -File scripts/health_check.ps1
if ($LASTEXITCODE -eq 0) {
    Write-Host "========================================================================" -ForegroundColor Green
    Write-Host "  [+] DEPLOYMENT COMPLETED SUCCESSFULLY" -ForegroundColor Green
    Write-Host "========================================================================" -ForegroundColor Green
    exit 0
} else {
    Write-Host "[-] Smoke tests failed! Initiating rollback..." -ForegroundColor Red
    powershell -File scripts/rollback.ps1
    exit 1
}
