#!/usr/bin/env python3
"""
CloudBox MinIO S3 Object Storage Restore Utility
Restores all objects from a local backup directory into the MinIO bucket.
"""

import os
import sys
from minio import Minio

MINIO_HOST = os.getenv("MINIO_HOST", "localhost")
MINIO_PORT = int(os.getenv("MINIO_API_PORT", 9000))
MINIO_ROOT_USER = os.getenv("MINIO_ROOT_USER", "cloudbox_admin")
MINIO_ROOT_PASSWORD = os.getenv("MINIO_ROOT_PASSWORD", "cloudbox_secret_key")
MINIO_DEFAULT_BUCKET = os.getenv("MINIO_DEFAULT_BUCKET", "cloudbox-uploads")

def restore_minio(backup_dir: str):
    if not os.path.isdir(backup_dir):
        print(f"[-] Backup directory not found: {backup_dir}", file=sys.stderr)
        return False

    endpoint = f"{MINIO_HOST}:{MINIO_PORT}"
    print(f"[*] Connecting to MinIO at {endpoint}...")
    try:
        client = Minio(
            endpoint,
            access_key=MINIO_ROOT_USER,
            secret_key=MINIO_ROOT_PASSWORD,
            secure=False
        )

        if not client.bucket_exists(MINIO_DEFAULT_BUCKET):
            client.make_bucket(MINIO_DEFAULT_BUCKET)
            print(f"[*] Created bucket '{MINIO_DEFAULT_BUCKET}'")

        restored = 0
        for root, _, files in os.walk(backup_dir):
            for file in files:
                full_path = os.path.join(root, file)
                # Compute object key relative to backup_dir
                rel_path = os.path.relpath(full_path, backup_dir).replace("\\", "/")
                client.fput_object(MINIO_DEFAULT_BUCKET, rel_path, full_path)
                restored += 1

        print(f"[+] MinIO restore finished: {restored} objects restored into '{MINIO_DEFAULT_BUCKET}'.")
        return True
    except Exception as e:
        print(f"[-] MinIO restore failed: {e}", file=sys.stderr)
        return False

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python restore_minio.py <path_to_backup_directory>")
        sys.exit(1)

    restore_minio(sys.argv[1])
