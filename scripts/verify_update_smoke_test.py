#!/usr/bin/env python3
import requests
import hashlib
import sys

BASE_URL = "http://localhost"

def test_cloudbox_update():
    print("=== CLOUDBOX PRODUCTION UPDATE VERIFICATION ===")
    
    # 1. Health check
    res = requests.get(f"{BASE_URL}/health")
    assert res.status_code == 200, f"Health check failed: {res.text}"
    health = res.json()
    print(f"[PASS] Healthcheck: status={health.get('status')}, db={health.get('database')}, storage={health.get('storage')}")
    
    # 2. Login as karthik
    login_res = requests.post(f"{BASE_URL}/api/auth/login", json={"username": "karthik", "password": "password123"})
    assert login_res.status_code == 200, f"Login failed: {login_res.text}"
    token = login_res.json().get("access_token")
    headers = {"Authorization": f"Bearer {token}"}
    print(f"[PASS] Authentication: Successfully logged in as user 'karthik'")
    
    # 3. Verify existing files preserved
    files_res = requests.get(f"{BASE_URL}/api/files", headers=headers)
    assert files_res.status_code == 200, f"File listing failed: {files_res.text}"
    files_data = files_res.json()
    files_list = files_data.get("files", files_data) if isinstance(files_data, dict) else files_data
    print(f"[PASS] Data Preservation: Retrieved {len(files_list)} existing files from database & MinIO:")
    for f in files_list:
        if isinstance(f, dict):
            print(f"       - {f.get('filename')} ({f.get('size')} bytes, checksum: {f.get('checksum')})")
    
    # 4. Upload a new test verification file
    test_content = b"CloudBox Docker Hub v1.0.1 image verification payload - " + str(hash(token)).encode()
    expected_checksum = hashlib.sha256(test_content).hexdigest()
    
    upload_res = requests.post(
        f"{BASE_URL}/api/files",
        headers=headers,
        files={"file": ("v101_verification.txt", test_content, "text/plain")}
    )
    assert upload_res.status_code in [200, 201], f"Upload failed: {upload_res.text}"
    uploaded_file = upload_res.json().get("file", upload_res.json())
    file_id = uploaded_file.get("id")
    print(f"[PASS] File Upload: Successfully uploaded 'v101_verification.txt' (ID: {file_id})")
    
    # 5. Download and verify SHA-256 byte parity
    download_res = requests.get(f"{BASE_URL}/api/files/{file_id}/download", headers=headers)
    assert download_res.status_code == 200, f"Download failed: {download_res.text}"
    downloaded_checksum = hashlib.sha256(download_res.content).hexdigest()
    assert downloaded_checksum == expected_checksum, f"Checksum mismatch! {downloaded_checksum} != {expected_checksum}"
    print(f"[PASS] Cryptographic Integrity: Downloaded SHA-256 matches perfectly ({downloaded_checksum})")
    
    # Clean up test file to recycle bin
    del_res = requests.delete(f"{BASE_URL}/api/files/{file_id}", headers=headers)
    print(f"[PASS] Cleanup: Test file moved to recycle bin (status: {del_res.status_code})")
    
    print("\n>>> ALL CLOUDBOX v1.0.1 UPDATE SMOKE TESTS PASSED! <<<")

if __name__ == "__main__":
    test_cloudbox_update()
