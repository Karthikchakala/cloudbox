#!/usr/bin/env python3
"""
CloudBox PostgreSQL Backup Utility
Creates timestamped, metadata-verified database dumps.
"""

import os
import sys
import time
import hashlib
import subprocess
from datetime import datetime

BACKUP_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "backups", "postgres"))

def ensure_dir(path: str):
    os.makedirs(path, exist_ok=True)

def create_postgres_backup(db_container="cloudbox-db", db_user="cloudbox_user", db_name="cloudbox_db", retention_count=10) -> str:
    ensure_dir(BACKUP_DIR)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_filename = f"backup_{db_name}_{timestamp}.sql"
    backup_path = os.path.join(BACKUP_DIR, backup_filename)

    print(f"[*] Starting PostgreSQL backup for '{db_name}'...")
    cmd = [
        "docker", "exec", db_container,
        "pg_dump", "-U", db_user, "-d", db_name, "--clean", "--if-exists"
    ]

    try:
        with open(backup_path, "w", encoding="utf-8") as f:
            proc = subprocess.run(cmd, stdout=f, stderr=subprocess.PIPE, text=True, check=True)
            
        size_bytes = os.path.getsize(backup_path)
        with open(backup_path, "rb") as f:
            checksum = hashlib.sha256(f.read()).hexdigest()

        meta_path = backup_path + ".meta"
        with open(meta_path, "w", encoding="utf-8") as meta_file:
            meta_file.write(f"timestamp={timestamp}\n")
            meta_file.write(f"database={db_name}\n")
            meta_file.write(f"size_bytes={size_bytes}\n")
            meta_file.write(f"sha256={checksum}\n")

        print(f"[+] Backup completed successfully: {backup_filename} ({size_bytes} bytes)")
        print(f"    SHA-256: {checksum}")

        # Enforce retention policy
        cleanup_old_backups(retention_count)
        return backup_path
    except subprocess.CalledProcessError as e:
        print(f"[-] Backup failed: {e.stderr}", file=sys.stderr)
        if os.path.exists(backup_path):
            os.remove(backup_path)
        return ""
    except Exception as e:
        print(f"[-] Unexpected error during backup: {e}", file=sys.stderr)
        return ""

def cleanup_old_backups(retention_count: int):
    backups = [f for f in os.listdir(BACKUP_DIR) if f.endswith(".sql")]
    backups.sort()
    if len(backups) > retention_count:
        to_delete = backups[:-retention_count]
        for f in to_delete:
            sql_path = os.path.join(BACKUP_DIR, f)
            meta_path = sql_path + ".meta"
            if os.path.exists(sql_path):
                os.remove(sql_path)
            if os.path.exists(meta_path):
                os.remove(meta_path)
            print(f"[*] Pruned old backup: {f}")

if __name__ == "__main__":
    create_postgres_backup()
