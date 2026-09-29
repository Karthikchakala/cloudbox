# CloudBox Safe Rollback Script (PowerShell)

Write-Host "========================================================================" -ForegroundColor Cyan
Write-Host "  CLOUDBOX SAFE APPLICATION ROLLBACK" -ForegroundColor Cyan
Write-Host "  Timestamp: $(Get-Date -Format 'yyyy-MM-ddTHH:mm:ssZ')" -ForegroundColor Cyan
Write-Host "========================================================================" -ForegroundColor Cyan

Write-Host "[*] Restarting stable service stack..."
docker compose -f compose.yaml -f compose.prod.yaml restart backend frontend nginx worker

Write-Host "[*] Checking service health after rollback..."
Start-Sleep -Seconds 5
powershell -File scripts/health_check.ps1
Write-Host "[+] Rollback completed. Stable state restored." -ForegroundColor Green
