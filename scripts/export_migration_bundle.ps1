<#
.SYNOPSIS
  CloudBox Automated Migration Bundle Exporter
.DESCRIPTION
  Safely snapshots PostgreSQL, MinIO storage objects, generates cryptographic SHA-256 manifests,
  and packages everything into a portable migration archive for deployment on a second laptop.
#>

$ErrorActionPreference = "Stop"

$BundleDir = "backups\migration_bundle"
$TempDir = "$BundleDir\extracted"
$ZipFile = "$BundleDir\cloudbox_migration_bundle.zip"

Write-Host "========================================================================" -ForegroundColor Cyan
Write-Host "  CLOUDBOX DATA-PRESERVING MIGRATION EXPORT" -ForegroundColor Cyan
Write-Host "========================================================================" -ForegroundColor Cyan

# Clean & Prepare Directories
if (Test-Path $TempDir) { Remove-Item -Recurse -Force $TempDir }
New-Item -ItemType Directory -Force -Path "$TempDir\database" | Out-Null
New-Item -ItemType Directory -Force -Path "$TempDir\minio" | Out-Null
New-Item -ItemType Directory -Force -Path "$TempDir\config" | Out-Null
New-Item -ItemType Directory -Force -Path "$TempDir\scripts" | Out-Null

# 1. Export PostgreSQL Dump
Write-Host "[1/5] Dumping PostgreSQL Database..." -ForegroundColor Yellow
docker exec -e PGPASSWORD=password123 cloudbox-db pg_dump -U cloudbox_user -d cloudbox_db -F c -b -v -f /tmp/pg_migration.dump
docker cp cloudbox-db:/tmp/pg_migration.dump "$TempDir\database\postgres_migration.dump"
docker exec cloudbox-db rm /tmp/pg_migration.dump
$dbSize = (Get-Item "$TempDir\database\postgres_migration.dump").Length
Write-Host "  -> PostgreSQL dump created: $dbSize bytes" -ForegroundColor Green

# 2. Export MinIO Objects & Manifest
Write-Host "[2/5] Exporting MinIO S3 Objects & Manifest..." -ForegroundColor Yellow
docker compose exec -T backend python -c "
import os, hashlib, json
from minio import Minio

client = Minio('minio:9000', access_key='cloudbox_admin', secret_key='password123', secure=False)
export_dir = '/app/backups/migration_bundle/extracted/minio'
os.makedirs(export_dir, exist_ok=True)

manifest = {}
buckets = client.list_buckets()
for b in buckets:
    bname = b.name
    bdir = os.path.join(export_dir, bname)
    os.makedirs(bdir, exist_ok=True)
    manifest[bname] = []
    
    for obj in client.list_objects(bname, recursive=True):
        dest = os.path.join(bdir, obj.object_name)
        os.makedirs(os.path.dirname(dest), exist_ok=True)
        client.fget_object(bname, obj.object_name, dest)
        with open(dest, 'rb') as f:
            h = hashlib.sha256(f.read()).hexdigest()
        manifest[bname].append({'key': obj.object_name, 'size': obj.size, 'sha256': h})

with open(os.path.join(export_dir, 'manifest.json'), 'w') as f:
    json.dump(manifest, f, indent=2)
print('MinIO export complete.')
"
Write-Host "  -> MinIO storage objects and SHA-256 manifest exported." -ForegroundColor Green

# 3. Copy Configurations and Deployment Files
Write-Host "[3/5] Bundling Compose Files and Templates..." -ForegroundColor Yellow
Copy-Item "compose.yaml" "$TempDir\config\compose.yaml"
Copy-Item "compose.prod.yaml" "$TempDir\config\compose.prod.yaml"
Copy-Item "compose.monitoring.yaml" "$TempDir\config\compose.monitoring.yaml"
Copy-Item ".env.example" "$TempDir\config\.env.example"
Copy-Item "scripts\verify_migration_integrity.py" "$TempDir\scripts\verify_migration_integrity.py"
Copy-Item "scripts\restore_migration_bundle.ps1" "$TempDir\scripts\restore_migration_bundle.ps1"

# 4. Generate Export Manifest & Checksums
Write-Host "[4/5] Generating Migration Metadata Manifest..." -ForegroundColor Yellow
$Manifest = @{
    ExportTimestamp = (Get-Date).ToString("yyyy-MM-ddTHH:mm:ssZ")
    SourceHost = $env:COMPUTERNAME
    PostgresDumpSize = $dbSize
    PostgresDumpSha256 = (Get-FileHash "$TempDir\database\postgres_migration.dump" -Algorithm SHA256).Hash
    MinIOObjectCount = (Get-ChildItem -Recurse -File "$TempDir\minio").Count
}
$Manifest | ConvertTo-Json -Depth 5 | Out-File "$TempDir\migration_metadata.json" -Encoding utf8

# 5. Compress into ZIP Archive
Write-Host "[5/5] Creating Migration ZIP Archive..." -ForegroundColor Yellow
if (Test-Path $ZipFile) { Remove-Item -Force $ZipFile }
Compress-Archive -Path "$TempDir\*" -DestinationPath $ZipFile -CompressionLevel Optimal
$zipSize = (Get-Item $ZipFile).Length / 1MB

Write-Host "========================================================================" -ForegroundColor Green
Write-Host "  MIGRATION BUNDLE CREATED SUCCESSFULLY!" -ForegroundColor Green
Write-Host "  Location: $ZipFile" -ForegroundColor Green
Write-Host "  Size: $([math]::Round($zipSize, 2)) MB" -ForegroundColor Green
Write-Host "========================================================================" -ForegroundColor Green
