# CloudBox Operational Health & Diagnostic Script (PowerShell)

Write-Host "========================================================================" -ForegroundColor Cyan
Write-Host "  CLOUDBOX SYSTEM HEALTH & DIAGNOSTIC CHECK" -ForegroundColor Cyan
Write-Host "  Timestamp: $(Get-Date -Format 'yyyy-MM-ddTHH:mm:ssZ')" -ForegroundColor Cyan
Write-Host "========================================================================" -ForegroundColor Cyan

$FailedCount = 0

function Test-ServiceEndpoint {
    param (
        [string]$Name,
        [string]$Url
    )
    Write-Host -NoNewline "[*] Checking $Name ($Url)... "
    try {
        $response = Invoke-WebRequest -Uri $Url -UseBasicParsing -TimeoutSec 5 -ErrorAction Stop
        if ($response.StatusCode -eq 200) {
            Write-Host "OK [PASS]" -ForegroundColor Green
        } else {
            Write-Host "FAILED ($($response.StatusCode)) [FAIL]" -ForegroundColor Red
            $script:FailedCount++
        }
    } catch {
        Write-Host "UNREACHABLE [FAIL]" -ForegroundColor Red
        $script:FailedCount++
    }
}

Test-ServiceEndpoint -Name "Nginx Reverse Proxy" -Url "http://localhost/nginx_health"
Test-ServiceEndpoint -Name "Backend API Health" -Url "http://localhost/health"
Test-ServiceEndpoint -Name "Prometheus Metrics" -Url "http://localhost:5000/api/metrics/prometheus"

Write-Host -NoNewline "[*] Checking Docker container states... "
$running = docker compose ps --status running -q
if ($running) {
    Write-Host "ALL RUNNING [PASS]" -ForegroundColor Green
} else {
    Write-Host "CONTAINERS NOT RUNNING [FAIL]" -ForegroundColor Red
    $FailedCount++
}

Write-Host "------------------------------------------------------------------------" -ForegroundColor Cyan
if ($FailedCount -eq 0) {
    Write-Host "[+] SYSTEM STATUS: ALL CHECKS PASSED [HEALTHY]" -ForegroundColor Green
    exit 0
} else {
    Write-Host "[-] SYSTEM STATUS: $FailedCount CHECKS FAILED [UNHEALTHY]" -ForegroundColor Red
    exit 1
}
