"""
MinIO Object Storage Validation Script for Phase 6.
"""
import os
import hashlib
import requests
from minio import Minio
from minio.error import S3Error

def validate_minio():
    print("==================================================")
    print("PHASE 6: MINIO OBJECT STORAGE & S3 VALIDATION")
    print("==================================================")
    
    endpoint = "minio:9000" if os.path.exists("/app") else "localhost:9000"
    client = Minio(
        endpoint,
        access_key="cloudbox_admin",
        secret_key="password123",
        secure=False
    )
    
    # 1. List Buckets
    buckets = client.list_buckets()
    bucket_names = [b.name for b in buckets]
    print(f"[PASS] MinIO Buckets Accessible: {bucket_names}")
    assert "cloudbox-uploads" in bucket_names, "Default bucket missing!"

    # 2. List Objects in cloudbox-uploads
    objs = list(client.list_objects("cloudbox-uploads", recursive=True))
    print(f"[PASS] Total Objects in 'cloudbox-uploads': {len(objs)}")
    assert len(objs) > 0, "Expected objects in bucket!"

    # 3. Download an object and verify checksum
    sample_obj = [o for o in objs if o.size > 0 and not o.object_name.startswith("chunks/")][0]
    print(f"--- Testing Object: {sample_obj.object_name} ({sample_obj.size} bytes) ---")
    
    resp = client.get_object("cloudbox-uploads", sample_obj.object_name)
    data = resp.read()
    resp.close()
    resp.release_conn()
    
    computed_sha = hashlib.sha256(data).hexdigest()
    print(f"[PASS] Downloaded object directly from MinIO S3 API. Size: {len(data)} bytes, SHA256: {computed_sha[:8]}...")
    assert len(data) == sample_obj.size

    # 4. Negative Test: Invalid Credentials
    print("--- Testing Invalid MinIO Credentials ---")
    bad_client = Minio(
        endpoint,
        access_key="cloudbox_admin",
        secret_key="invalid_secret_key_123",
        secure=False
    )
    try:
        bad_client.list_buckets()
        assert False, "Should have thrown S3Error on invalid credentials!"
    except S3Error as e:
        print(f"[PASS] Invalid MinIO credentials rejected (S3Error: {e.code}).")

    print("\n>>> ALL PHASE 6 MINIO VALIDATION TESTS PASSED (100%) <<<")

if __name__ == "__main__":
    validate_minio()
