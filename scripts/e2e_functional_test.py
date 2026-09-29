#!/usr/bin/env python3
"""
CloudBox Phase 8: Comprehensive End-to-End Functional Validation Suite
Validates the complete full-stack user workflow against live running containers.
"""

import sys
import time
import uuid
import hashlib
import io
import requests

BASE_URL = "http://localhost/api"
TIMEOUT = 10

class FunctionalTestTracker:
    def __init__(self):
        self.passed = 0
        self.failed = 0
        self.results = []

    def record(self, name, success, details=""):
        status = "PASS" if success else "FAIL"
        if success:
            self.passed += 1
            print(f"  [PASS] {name} {details}")
        else:
            self.failed += 1
            print(f"  [FAIL] {name} - ERROR: {details}")
        self.results.append({
            "name": name,
            "status": status,
            "details": details
        })

    def summary(self):
        total = self.passed + self.failed
        print("\n" + "=" * 60)
        print(f"E2E VALIDATION SUMMARY: {self.passed}/{total} PASSED ({(self.passed/total)*100:.1f}%)")
        print("=" * 60)
        return self.failed == 0

def run_e2e_tests():
    print("============================================================")
    print(" CloudBox Phase 8 - End-to-End Functional Validation Suite")
    print("============================================================")
    tracker = FunctionalTestTracker()

    session_a = requests.Session()
    session_b = requests.Session()

    # Generate unique test user credentials
    uid_a = uuid.uuid4().hex[:8]
    uid_b = uuid.uuid4().hex[:8]
    user_a = {
        "username": f"e2e_user_{uid_a}",
        "email": f"e2e_user_{uid_a}@cloudbox.local",
        "password": "E2eSecurePassword123!"
    }
    user_b = {
        "username": f"e2e_user_{uid_b}",
        "email": f"e2e_user_{uid_b}@cloudbox.local",
        "password": "E2eSecurePassword456!"
    }

    print("\n[1] Authentication & Access Control Tests")
    # 1.1 Register User A
    try:
        r = session_a.post(f"{BASE_URL}/auth/register", json=user_a, timeout=TIMEOUT)
        tracker.record("1.1 Register User A", r.status_code == 201, f"Status: {r.status_code}")
    except Exception as e:
        tracker.record("1.1 Register User A", False, str(e))

    # 1.2 Duplicate Registration Rejection
    try:
        r = session_a.post(f"{BASE_URL}/auth/register", json=user_a, timeout=TIMEOUT)
        tracker.record("1.2 Duplicate Registration Rejection", r.status_code in [400, 409], f"Status: {r.status_code}")
    except Exception as e:
        tracker.record("1.2 Duplicate Registration Rejection", False, str(e))

    # 1.3 Login User A
    token_a = None
    try:
        r = session_a.post(f"{BASE_URL}/auth/login", json={"email": user_a["email"], "password": user_a["password"]}, timeout=TIMEOUT)
        if r.status_code == 200:
            token_a = r.json().get("access_token")
            session_a.headers.update({"Authorization": f"Bearer {token_a}"})
            tracker.record("1.3 Login User A & JWT Issuance", True, "Token acquired")
        else:
            tracker.record("1.3 Login User A & JWT Issuance", False, f"Status: {r.status_code}")
    except Exception as e:
        tracker.record("1.3 Login User A & JWT Issuance", False, str(e))

    # 1.4 Register and Login User B
    token_b = None
    try:
        r = session_b.post(f"{BASE_URL}/auth/register", json=user_b, timeout=TIMEOUT)
        r_login = session_b.post(f"{BASE_URL}/auth/login", json={"email": user_b["email"], "password": user_b["password"]}, timeout=TIMEOUT)
        if r_login.status_code == 200:
            token_b = r_login.json().get("access_token")
            session_b.headers.update({"Authorization": f"Bearer {token_b}"})
            tracker.record("1.4 Register & Login User B", True, "Token acquired")
        else:
            tracker.record("1.4 Register & Login User B", False, f"Status: {r_login.status_code}")
    except Exception as e:
        tracker.record("1.4 Register & Login User B", False, str(e))

    # 1.5 Current User Profile Validation
    try:
        r = session_a.get(f"{BASE_URL}/auth/me", timeout=TIMEOUT)
        user_name_match = r.status_code == 200 and r.json().get("user", {}).get("username") == user_a["username"]
        tracker.record("1.5 Current User Profile Verification", user_name_match, f"Username: {r.json().get('user', {}).get('username')}")
    except Exception as e:
        tracker.record("1.5 Current User Profile Verification", False, str(e))

    # 1.6 Unauthorized Request Rejection
    try:
        r = requests.get(f"{BASE_URL}/files", timeout=TIMEOUT)
        tracker.record("1.6 Unauthorized Access Prevention", r.status_code == 401, f"Status: {r.status_code}")
    except Exception as e:
        tracker.record("1.6 Unauthorized Access Prevention", False, str(e))

    print("\n[2] File Management & Storage Integrity Tests")
    # 2.1 File Upload
    file_content = b"CloudBox Phase 8 E2E Test Payload with unique cryptographic entropy: " + uuid.uuid4().bytes
    expected_checksum = hashlib.sha256(file_content).hexdigest()
    file_a_id = None
    try:
        files = {"file": ("e2e_document.txt", io.BytesIO(file_content), "text/plain")}
        r = session_a.post(f"{BASE_URL}/files", files=files, timeout=TIMEOUT)
        if r.status_code in [200, 201]:
            file_data = r.json()
            file_a_id = file_data.get("id") or file_data.get("file", {}).get("id")
            tracker.record("2.1 File Upload", True, f"File ID: {file_a_id}")
        else:
            tracker.record("2.1 File Upload", False, f"Status: {r.status_code}, Body: {r.text}")
    except Exception as e:
        tracker.record("2.1 File Upload", False, str(e))

    # 2.2 File Listing
    try:
        r = session_a.get(f"{BASE_URL}/files", timeout=TIMEOUT)
        files_list = r.json().get("files", [])
        found = any(f.get("id") == file_a_id for f in files_list)
        tracker.record("2.2 File Listing Verification", r.status_code == 200 and found, f"Total files: {len(files_list)}")
    except Exception as e:
        tracker.record("2.2 File Listing Verification", False, str(e))

    # 2.3 File Download and Checksum Verification
    try:
        r = session_a.get(f"{BASE_URL}/files/{file_a_id}/download", timeout=TIMEOUT)
        downloaded_content = r.content
        actual_checksum = hashlib.sha256(downloaded_content).hexdigest()
        match = (actual_checksum == expected_checksum)
        tracker.record("2.3 File Download & SHA-256 Checksum Match", r.status_code == 200 and match, f"Checksum: {actual_checksum[:12]}...")
    except Exception as e:
        tracker.record("2.3 File Download & SHA-256 Checksum Match", False, str(e))

    # 2.4 Multi-User Isolation
    try:
        r = session_b.get(f"{BASE_URL}/files/{file_a_id}/download", timeout=TIMEOUT)
        tracker.record("2.4 Cross-User Data Isolation Protection", r.status_code in [403, 404], f"User B blocked with status: {r.status_code}")
    except Exception as e:
        tracker.record("2.4 Cross-User Data Isolation Protection", False, str(e))

    print("\n[3] File Versioning Tests")
    # 3.1 Upload Version 2
    v2_content = b"CloudBox Version 2 Updated Content payload: " + uuid.uuid4().bytes
    v2_checksum = hashlib.sha256(v2_content).hexdigest()
    try:
        files = {"file": ("e2e_document.txt", io.BytesIO(v2_content), "text/plain")}
        r = session_a.post(f"{BASE_URL}/files/{file_a_id}/versions", files=files, timeout=TIMEOUT)
        tracker.record("3.1 Upload File Version 2", r.status_code in [200, 201], f"Status: {r.status_code}")
    except Exception as e:
        tracker.record("3.1 Upload File Version 2", False, str(e))

    # 3.2 List File Versions
    versions_list = []
    try:
        r = session_a.get(f"{BASE_URL}/files/{file_a_id}/versions", timeout=TIMEOUT)
        versions_list = r.json().get("versions", [])
        tracker.record("3.2 List Historical Versions", len(versions_list) >= 2, f"Total versions: {len(versions_list)}")
    except Exception as e:
        tracker.record("3.2 List Historical Versions", False, str(e))

    # 3.3 Restore Historical Version (Version 1)
    try:
        v1_record = next((v for v in versions_list if v.get("version_number") == 1), None)
        v1_id = v1_record.get("id") if v1_record else None
        if v1_id:
            r = session_a.post(f"{BASE_URL}/files/{file_a_id}/versions/{v1_id}/restore", timeout=TIMEOUT)
            tracker.record("3.3 Restore Historical Version 1", r.status_code in [200, 201], f"Status: {r.status_code}")
        else:
            tracker.record("3.3 Restore Historical Version 1", False, "Could not find Version 1 ID")
    except Exception as e:
        tracker.record("3.3 Restore Historical Version 1", False, str(e))

    print("\n[4] Sharing Links & Access Permissions Tests")
    # 4.1 Create Public Share Link
    share_token = None
    share_id = None
    try:
        r = session_a.post(f"{BASE_URL}/files/{file_a_id}/shares", json={"max_downloads": 5}, timeout=TIMEOUT)
        if r.status_code in [200, 201]:
            data = r.json()
            share_token = data.get("token")
            share_id = data.get("share", {}).get("id")
            tracker.record("4.1 Create Public Share Link", bool(share_token and share_id), f"Token: {share_token[:12]}...")
        else:
            tracker.record("4.1 Create Public Share Link", False, f"Status: {r.status_code}")
    except Exception as e:
        tracker.record("4.1 Create Public Share Link", False, str(e))

    # 4.2 Download via Public Share Link (Anonymous)
    try:
        r = requests.get(f"{BASE_URL}/shared/{share_token}?download=true", timeout=TIMEOUT)
        tracker.record("4.2 Anonymous Download via Share Link", r.status_code == 200 and len(r.content) > 0, f"Bytes: {len(r.content)}")
    except Exception as e:
        tracker.record("4.2 Anonymous Download via Share Link", False, str(e))

    # 4.3 Revoke Share Link
    try:
        r = session_a.delete(f"{BASE_URL}/shares/{share_id}", timeout=TIMEOUT)
        r_access = requests.get(f"{BASE_URL}/shared/{share_token}?download=true", timeout=TIMEOUT)
        tracker.record("4.3 Revoke Share Link & Confirm Invalidation", r.status_code == 200 and r_access.status_code in [403, 404, 410], f"Access status after revocation: {r_access.status_code}")
    except Exception as e:
        tracker.record("4.3 Revoke Share Link & Confirm Invalidation", False, str(e))

    print("\n[5] Recycle Bin & Soft Delete Lifecycle Tests")
    # 5.1 Soft Delete (Move to Trash)
    try:
        r = session_a.delete(f"{BASE_URL}/files/{file_a_id}", timeout=TIMEOUT)
        tracker.record("5.1 Move File to Recycle Bin", r.status_code == 200, f"Status: {r.status_code}")
    except Exception as e:
        tracker.record("5.1 Move File to Recycle Bin", False, str(e))

    # 5.2 Verify Active File List Excludes Trashed File
    try:
        r = session_a.get(f"{BASE_URL}/files", timeout=TIMEOUT)
        files_list = r.json().get("files", [])
        not_in_active = not any(f.get("id") == file_a_id for f in files_list)
        tracker.record("5.2 Verify Active List Excludes Trashed File", not_in_active, "Active list clean")
    except Exception as e:
        tracker.record("5.2 Verify Active List Excludes Trashed File", False, str(e))

    # 5.3 List Trash
    try:
        r = session_a.get(f"{BASE_URL}/trash", timeout=TIMEOUT)
        trash_list = r.json().get("files", [])
        found_in_trash = any(f.get("id") == file_a_id for f in trash_list)
        tracker.record("5.3 Verify File Present in Recycle Bin", found_in_trash, f"Trash items: {len(trash_list)}")
    except Exception as e:
        tracker.record("5.3 Verify File Present in Recycle Bin", False, str(e))

    # 5.4 Restore File from Trash
    try:
        r = session_a.post(f"{BASE_URL}/trash/{file_a_id}/restore", timeout=TIMEOUT)
        tracker.record("5.4 Restore File from Recycle Bin", r.status_code == 200, f"Status: {r.status_code}")
    except Exception as e:
        tracker.record("5.4 Restore File from Recycle Bin", False, str(e))

    print("\n[6] Resumable Chunked Multi-Part Upload Tests")
    # 6.1 Initiate Chunked Upload Session
    chunk_file_content = b"Multi-Part Resumable Chunked Upload Segment Data Block " * 5000  # ~275 KB
    chunk_checksum = hashlib.sha256(chunk_file_content).hexdigest()
    chunk_size = 64 * 1024  # 64 KB
    chunks = [chunk_file_content[i:i+chunk_size] for i in range(0, len(chunk_file_content), chunk_size)]
    session_id = None
    try:
        init_payload = {
            "filename": "chunked_test_file.bin",
            "file_size": len(chunk_file_content),
            "content_type": "application/octet-stream",
            "chunk_size": chunk_size
        }
        r = session_a.post(f"{BASE_URL}/uploads/initiate", json=init_payload, timeout=TIMEOUT)
        if r.status_code in [200, 201]:
            session_id = r.json().get("upload_id")
            tracker.record("6.1 Initiate Chunked Upload Session", bool(session_id), f"Session ID: {session_id}")
        else:
            tracker.record("6.1 Initiate Chunked Upload Session", False, f"Status: {r.status_code}")
    except Exception as e:
        tracker.record("6.1 Initiate Chunked Upload Session", False, str(e))

    # 6.2 Upload All Chunks (1-indexed)
    chunks_ok = True
    try:
        for idx, chunk_data in enumerate(chunks, start=1):
            headers = {"Content-Type": "application/octet-stream"}
            r = session_a.put(f"{BASE_URL}/uploads/{session_id}/chunks/{idx}", data=chunk_data, headers=headers, timeout=TIMEOUT)
            if r.status_code not in [200, 201]:
                chunks_ok = False
                break
        tracker.record("6.2 Upload All Multi-Part Chunks", chunks_ok, f"Uploaded {len(chunks)} chunks")
    except Exception as e:
        tracker.record("6.2 Upload All Multi-Part Chunks", False, str(e))

    # 6.3 Complete Chunked Upload & Reassemble
    chunked_file_id = None
    try:
        r = session_a.post(f"{BASE_URL}/uploads/{session_id}/complete", timeout=TIMEOUT)
        if r.status_code in [200, 201]:
            file_data = r.json().get("file", {})
            chunked_file_id = file_data.get("id")
            tracker.record("6.3 Complete & Reassemble Chunked Upload", bool(chunked_file_id), f"Created File ID: {chunked_file_id}")
        else:
            tracker.record("6.3 Complete & Reassemble Chunked Upload", False, f"Status: {r.status_code}, Body: {r.text}")
    except Exception as e:
        tracker.record("6.3 Complete & Reassemble Chunked Upload", False, str(e))

    # 6.4 Download Reassembled File & Verify Exact Checksum
    try:
        r = session_a.get(f"{BASE_URL}/files/{chunked_file_id}/download", timeout=TIMEOUT)
        reassembled_checksum = hashlib.sha256(r.content).hexdigest()
        tracker.record("6.4 Verify Reassembled Checksum Integrity", reassembled_checksum == chunk_checksum, f"Size: {len(r.content)} bytes, Checksum Match: True")
    except Exception as e:
        tracker.record("6.4 Verify Reassembled Checksum Integrity", False, str(e))

    print("\n[7] Telemetry & Operational Health Endpoints")
    # 7.1 Health Endpoint
    try:
        r = requests.get("http://localhost/health", timeout=TIMEOUT)
        tracker.record("7.1 API Health Check (/health)", r.status_code == 200 and r.json().get("status") == "healthy", f"Status: {r.json().get('status')}")
    except Exception as e:
        tracker.record("7.1 API Health Check (/health)", False, str(e))

    # 7.2 Prometheus Metrics Exposition
    try:
        r = requests.get(f"{BASE_URL}/metrics/prometheus", timeout=TIMEOUT)
        has_metrics = "cloudbox_uptime_seconds" in r.text and "cloudbox_db_up" in r.text
        tracker.record("7.2 Prometheus Metrics Exposition (/api/metrics/prometheus)", r.status_code == 200 and has_metrics, "Prometheus text format verified")
    except Exception as e:
        tracker.record("7.2 Prometheus Metrics Exposition (/api/metrics/prometheus)", False, str(e))

    success = tracker.summary()
    return 0 if success else 1

if __name__ == "__main__":
    sys.exit(run_e2e_tests())
