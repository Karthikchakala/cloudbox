# MinIO Object Storage Configuration

This directory contains configuration, scripts, or policy definitions for MinIO in CloudBox.

## Default Credentials (Development)
- **Root User**: Specified by `MINIO_ROOT_USER` in `.env` (default: `cloudbox_admin`)
- **Root Password**: Specified by `MINIO_ROOT_PASSWORD` in `.env` (default: `cloudbox_secret_key`)

## Ports
- **API (S3-compatible endpoint)**: 9000
- **Web Console**: 9001

## Persistent Storage
Object data is stored inside Docker named volume `minio_data` mounted at `/data`.
