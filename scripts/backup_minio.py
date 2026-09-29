#!/usr/bin/env python3
"""
CloudBox MinIO S3 Object Storage Backup Utility
Downloads all stored objects from the specified bucket to a timestamped local backup archive.
"""

import os
import sys
import io
from datetime import datetime
from minio import Minio

MINIO_HOST = os.getenv("MINIO_HOST", "localhost")
MINIO_PORT = int(os.getenv("MINIO_API_PORT", 9000))
MINIO_ROOT_USER = os.getenv("MINIO_ROOT_USER", "cloudbox_admin")
MINIO_ROOT_PASSWORD = os.getenv("MINIO_ROOT_PASSWORD", "cloudbox_secret_key")
MINIO_DEFAULT_BUCKET = os.getenv("MINIO_DEFAULT_BUCKET", "cloudbox-uploads")

BACKUP_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "backups", "minio"))

def create_minio_backup():
    os.makedirs(BACKUP_ROOT, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    target_dir = os.path.join(BACKUP_ROOT, f"backup_minio_{timestamp}")
    os.makedirs(target_dir, exist_ok=True)

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
            print(f"[-] Bucket {MINIO_DEFAULT_BUCKET} does not exist.")
            return

        objects = list(client.list_objects(MINIO_DEFAULT_BUCKET, recursive=True))
        print(f"[*] Found {len(objects)} objects in bucket '{MINIO_DEFAULT_BUCKET}' to back up.")

        count = 0
        total_bytes = 0
        for obj in objects:
            dest_file = os.path.join(target_dir, obj.object_name)
            os.makedirs(os.path.dirname(dest_file), exist_ok=True)
            client.fget_object(MINIO_DEFAULT_BUCKET, obj.object_name, dest_file)
            count += 1
            total_bytes += obj.size

        print(f"[+] MinIO backup finished successfully: {count} objects ({total_bytes} bytes) saved to:")
        print(f"    {target_dir}")
        return target_dir
    except Exception as e:
        print(f"[-] MinIO backup failed: {e}", file=sys.stderr)
        return None

if __name__ == "__main__":
    create_minio_backup()
