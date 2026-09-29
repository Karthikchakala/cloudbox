#!/usr/bin/env python3
"""
CloudBox PostgreSQL Restore Utility
Safely restores a chosen SQL dump into the PostgreSQL container.
"""

import os
import sys
import subprocess

BACKUP_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "backups", "postgres"))

def list_backups():
    if not os.path.exists(BACKUP_DIR):
        print(f"[-] No backups directory found at {BACKUP_DIR}")
        return []
    backups = [f for f in os.listdir(BACKUP_DIR) if f.endswith(".sql")]
    backups.sort()
    return backups

def restore_postgres(backup_file: str, db_container="cloudbox-db", db_user="cloudbox_user", db_name="cloudbox_db"):
    if not os.path.isabs(backup_file):
        backup_path = os.path.join(BACKUP_DIR, backup_file)
    else:
        backup_path = backup_file

    if not os.path.isfile(backup_path):
        print(f"[-] Backup file not found: {backup_path}", file=sys.stderr)
        return False

    print(f"[*] Restoring database '{db_name}' from {os.path.basename(backup_path)}...")
    cmd = ["docker", "exec", "-i", db_container, "psql", "-U", db_user, "-d", db_name]

    try:
        with open(backup_path, "r", encoding="utf-8") as f:
            proc = subprocess.run(cmd, stdin=f, capture_output=True, text=True, check=True)
        print(f"[+] Database restore completed successfully!")
        return True
    except subprocess.CalledProcessError as e:
        print(f"[-] Restore error: {e.stderr}", file=sys.stderr)
        return False
    except Exception as e:
        print(f"[-] Unexpected error during restore: {e}", file=sys.stderr)
        return False

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python restore_postgres.py <backup_filename_or_path>")
        print("\nAvailable backups:")
        for b in list_backups():
            print(f"  - {b}")
        sys.exit(1)

    target_file = sys.argv[1]
    restore_postgres(target_file)
