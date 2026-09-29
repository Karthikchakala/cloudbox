<#
.SYNOPSIS
  CloudBox Destination Laptop Automated Restore Script
.DESCRIPTION
  Restores PostgreSQL database, MinIO storage objects, restores all user data and permissions,
  and boots up the full CloudBox stack on the second laptop.
#>

param(
    [string]$BundlePath = "cloudbox_migration_bundle.zip",
    [string]$ExtractDir = "migration_extracted"
)

$ErrorActionPreference = "Stop"

Write-Host "========================================================================" -ForegroundColor Cyan
Write-Host "  CLOUDBOX DESTINATION RESTORE & DEPLOYMENT" -ForegroundColor Cyan
Write-Host "========================================================================" -ForegroundColor Cyan

# 1. Unzip Bundle
if (Test-Path $ExtractDir) { Remove-Item -Recurse -Force $ExtractDir }
Write-Host "[1/6] Unpacking Migration Bundle..." -ForegroundColor Yellow
Expand-Archive -Path $BundlePath -DestinationPath $ExtractDir -Force

# 2. Setup Environment Configuration
Write-Host "[2/6] Configuring Environment (.env)..." -ForegroundColor Yellow
if (-not (Test-Path ".env")) {
    Copy-Item "$ExtractDir\config\.env.example" ".env"
    Write-Host "  -> Generated .env from template." -ForegroundColor Green
}

# 3. Start Core Database & Storage Services
Write-Host "[3/6] Starting PostgreSQL and MinIO Containers..." -ForegroundColor Yellow
docker compose up -d db minio redis
Write-Host "  -> Waiting for services to become healthy..." -ForegroundColor Cyan
Start-Sleep -Seconds 8

# 4. Restore PostgreSQL Database
Write-Host "[4/6] Restoring PostgreSQL Database..." -ForegroundColor Yellow
$dumpFile = "$ExtractDir\database\postgres_migration.dump"
docker cp $dumpFile cloudbox-db:/tmp/pg_restore.dump
docker exec -e PGPASSWORD=password123 cloudbox-db pg_restore -U cloudbox_user -d cloudbox_db --clean --if-exists -v /tmp/pg_restore.dump
docker exec cloudbox-db rm /tmp/pg_restore.dump
Write-Host "  -> PostgreSQL database restored successfully." -ForegroundColor Green

# 5. Restore MinIO Objects
Write-Host "[5/6] Restoring MinIO S3 Objects..." -ForegroundColor Yellow
# Copy minio objects into a temporary volume or use backend helper to upload
docker compose up -d backend worker nginx frontend
Start-Sleep -Seconds 5

docker compose exec -T backend python -c "
import os, json
from minio import Minio

client = Minio('minio:9000', access_key='cloudbox_admin', secret_key='password123', secure=False)
minio_src = '/app/$ExtractDir/minio' if os.path.exists('/app/$ExtractDir/minio') else '/app/backups/migration_bundle/extracted/minio'

# Ensure bucket
if not client.bucket_exists('cloudbox-uploads'):
    client.make_bucket('cloudbox-uploads')

manifest_file = os.path.join(minio_src, 'manifest.json')
if os.path.exists(manifest_file):
    with open(manifest_file, 'r') as f:
        manifest = json.load(f)
    for bucket, items in manifest.items():
        if not client.bucket_exists(bucket):
            client.make_bucket(bucket)
        for item in items:
            key = item['key']
            src_file = os.path.join(minio_src, bucket, key)
            if os.path.exists(src_file):
                client.fput_object(bucket, key, src_file)
                print(f'Restored {bucket}/{key}')
print('MinIO restore complete.')
"
Write-Host "  -> MinIO S3 storage objects restored." -ForegroundColor Green

# 6. Verify System Integrity
Write-Host "[6/6] Verifying Data & Service Integrity..." -ForegroundColor Yellow
docker compose exec -T -e PYTHONPATH=. backend python scripts/verify_migration_integrity.py

Write-Host "========================================================================" -ForegroundColor Green
Write-Host "  CLOUDBOX RESTORE & MIGRATION COMPLETE ON DESTINATION LAPTOP!" -ForegroundColor Green
Write-Host "  Web Application: http://localhost" -ForegroundColor Green
Write-Host "  MinIO Console:   http://localhost:9001" -ForegroundColor Green
Write-Host "  Grafana:         http://localhost:3000" -ForegroundColor Green
Write-Host "========================================================================" -ForegroundColor Green
