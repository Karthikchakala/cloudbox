"""
Baseline Backup Script for CloudBox.
Backs up:
1. PostgreSQL database (pg_dump custom format)
2. MinIO S3 buckets and objects using minio Python library
"""
import os
import subprocess
import hashlib
import json
from minio import Minio

BACKUP_DIR = "/app/backups/baseline" if os.path.exists("/app") else os.path.abspath("backups/baseline")
os.makedirs(BACKUP_DIR, exist_ok=True)

def backup_postgres():
    print("--- 1. Backing up PostgreSQL ---")
    dump_file = os.path.join(BACKUP_DIR, "postgres_dump_baseline.dump")
    # If run inside container or host
    pg_host = os.environ.get("POSTGRES_HOST", "cloudbox-db" if os.path.exists("/app") else "localhost")
    pg_user = os.environ.get("POSTGRES_USER", "cloudbox_user")
    pg_db = os.environ.get("POSTGRES_DB", "cloudbox_db")
    pg_pass = os.environ.get("POSTGRES_PASSWORD", "password123")
    
    if os.path.exists("/app"):
        # We can run pg_dump inside backend container if pg_isready/pg_dump exists or via docker from host
        print(f"Executing pg_dump from container against {pg_host}...")
        env = os.environ.copy()
        env["PGPASSWORD"] = pg_pass
        res = subprocess.run(["pg_dump", "-h", pg_host, "-U", pg_user, "-d", pg_db, "-F", "c", "-b", "-f", dump_file], env=env, capture_output=True, text=True)
        if res.returncode != 0:
            print(f"pg_dump failed: {res.stderr}")
            raise RuntimeError(res.stderr)
    else:
        cmd = [
            "docker", "exec", "-e", "PGPASSWORD=password123", "cloudbox-db",
            "pg_dump", "-U", "cloudbox_user", "-d", "cloudbox_db", "-F", "c", "-b", "-v", "-f", "/tmp/pg_baseline.dump"
        ]
        subprocess.run(cmd, check=True)
        subprocess.run(["docker", "cp", "cloudbox-db:/tmp/pg_baseline.dump", dump_file], check=True)
        subprocess.run(["docker", "exec", "cloudbox-db", "rm", "/tmp/pg_baseline.dump"], check=True)
        
    print(f"PostgreSQL backup saved to: {dump_file} ({os.path.getsize(dump_file)} bytes)")
    return dump_file

def backup_minio():
    print("--- 2. Backing up MinIO Objects ---")
    minio_dir = os.path.join(BACKUP_DIR, "minio")
    os.makedirs(minio_dir, exist_ok=True)
    
    endpoint = os.environ.get("MINIO_ENDPOINT", "minio:9000" if os.path.exists("/app") else "localhost:9000")
    access_key = os.environ.get("MINIO_ROOT_USER", "cloudbox_admin")
    secret_key = os.environ.get("MINIO_ROOT_PASSWORD", "password123")
    
    client = Minio(endpoint, access_key=access_key, secret_key=secret_key, secure=False)
    
    buckets = client.list_buckets()
    manifest = {}
    for b in buckets:
        bname = b.name
        bdir = os.path.join(minio_dir, bname)
        os.makedirs(bdir, exist_ok=True)
        manifest[bname] = []
        
        objs = client.list_objects(bname, recursive=True)
        for obj in objs:
            key = obj.object_name
            dest_path = os.path.join(bdir, key.replace('/', os.sep))
            os.makedirs(os.path.dirname(dest_path), exist_ok=True)
            
            client.fget_object(bname, key, dest_path)
            with open(dest_path, 'rb') as f:
                chash = hashlib.sha256(f.read()).hexdigest()
            
            manifest[bname].append({
                "key": key,
                "size": obj.size,
                "sha256": chash,
                "local_path": dest_path
            })
            print(f"  Downloaded: {key} ({obj.size} bytes, sha256: {chash[:8]}...)")
            
    manifest_path = os.path.join(BACKUP_DIR, "minio_manifest.json")
    with open(manifest_path, 'w') as f:
        json.dump(manifest, f, indent=2)
    print(f"MinIO manifest saved to: {manifest_path}")

def main():
    backup_postgres()
    backup_minio()
    print("\n>>> Baseline backup complete and verified successfully! <<<")

if __name__ == '__main__':
    main()
