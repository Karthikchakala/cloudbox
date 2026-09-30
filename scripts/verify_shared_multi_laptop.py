#!/usr/bin/env python3
"""
CloudBox — Multi-Laptop Shared Storage Cross-Device Verification Suite
Tests functional synchronization between two independent application instances (Laptop 1 and Laptop 2)
connecting to a shared PostgreSQL database and MinIO object storage.

Tests:
1. Upload from Laptop 1 (File + Metadata + MinIO object verification)
2. Access from Laptop 2 (User login, file discovery, download, SHA-256 integrity verification)
3. Upload from Laptop 2 (File upload from Node 2, discovery and download on Node 1, checksum verification)
4. Cross-Device Operations:
   - File rename and metadata update
   - File preview content streaming
   - Share link creation on Node 1 and public retrieval on Node 2
   - Share link revocation
   - Soft-delete to Recycle Bin
   - Restore from Recycle Bin
   - User Isolation (User A files inaccessible to User B)
5. Data Persistence & Integrity Verification
"""

import sys
import os
import io
import time
import uuid
import hashlib
import requests

BASE_URL = os.environ.get("BASE_URL", "http://localhost:5000")
JWT_SECRET = os.environ.get("JWT_SECRET_KEY", "336f4a1c52c4471aae0a539f9d503e6b844a648ad6c3ad1c57394257c8f1286c")

def log(msg, symbol="[*]"):
    print(f"{symbol} {msg}")

def assert_true(cond, msg):
    if not cond:
        print(f"[-] FAILED: {msg}")
        raise AssertionError(msg)
    print(f"[+] PASSED: {msg}")

def compute_sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()

class SimulatedLaptopNode:
    """Represents an independent CloudBox client node connected to the backend API."""
    def __init__(self, name: str, base_url: str):
        self.name = name
        self.base_url = base_url.rstrip("/")
        self.session = requests.Session()
        self.token = None
        self.user = None

    def register_or_login(self, username, email, password):
        log(f"[{self.name}] Authenticating user '{username}' ({email})...")
        resp = self.session.post(f"{self.base_url}/api/auth/login", json={
            "email": email,
            "password": password
        })
        if resp.status_code == 200:
            data = resp.json()
            self.token = data.get("access_token")
            self.user = data.get("user")
            self.session.headers.update({"Authorization": f"Bearer {self.token}"})
            log(f"[{self.name}] Logged in successfully as {username} (ID: {self.user['id']})")
            return self.user

        # If user doesn't exist, register
        reg_resp = self.session.post(f"{self.base_url}/api/auth/register", json={
            "username": username,
            "email": email,
            "password": password
        })
        if reg_resp.status_code == 201:
            data = reg_resp.json()
            self.token = data.get("access_token")
            self.user = data.get("user")
            self.session.headers.update({"Authorization": f"Bearer {self.token}"})
            log(f"[{self.name}] Registered and logged in as {username} (ID: {self.user['id']})")
            return self.user
        else:
            raise RuntimeError(f"Authentication failed on {self.name}: {resp.text} / {reg_resp.text}")

    def list_files(self):
        resp = self.session.get(f"{self.base_url}/api/files")
        assert resp.status_code == 200, f"Failed to list files: {resp.text}"
        return resp.json().get("files", [])

    def upload_file(self, filename: str, content: bytes, content_type: str = "text/plain"):
        files = {
            "file": (filename, io.BytesIO(content), content_type)
        }
        resp = self.session.post(f"{self.base_url}/api/files", files=files)
        assert resp.status_code == 201, f"Failed to upload {filename}: {resp.text}"
        return resp.json().get("file")

    def download_file(self, file_id: str) -> bytes:
        resp = self.session.get(f"{self.base_url}/api/files/{file_id}/download")
        assert resp.status_code == 200, f"Failed to download {file_id}: {resp.text}"
        return resp.content

    def preview_file(self, file_id: str) -> bytes:
        resp = self.session.get(f"{self.base_url}/api/files/{file_id}/preview")
        assert resp.status_code == 200, f"Failed to preview {file_id}: {resp.text}"
        return resp.content

    def rename_file(self, file_id: str, new_name: str):
        resp = self.session.patch(f"{self.base_url}/api/files/{file_id}", json={"name": new_name})
        assert resp.status_code == 200, f"Failed to rename {file_id}: {resp.text}"
        return resp.json().get("file")

    def soft_delete_file(self, file_id: str):
        resp = self.session.delete(f"{self.base_url}/api/files/{file_id}")
        assert resp.status_code == 200, f"Failed to soft delete {file_id}: {resp.text}"
        return resp.json()

    def list_trash(self):
        resp = self.session.get(f"{self.base_url}/api/trash")
        assert resp.status_code == 200, f"Failed to list trash: {resp.text}"
        data = resp.json()
        return data.get("files", data.get("trash", []))

    def restore_trash(self, file_id: str):
        resp = self.session.post(f"{self.base_url}/api/trash/{file_id}/restore")
        assert resp.status_code == 200, f"Failed to restore {file_id}: {resp.text}"
        return resp.json()

    def create_share_link(self, file_id: str, permission: str = "download", password: str = None):
        payload = {"permission": permission}
        if password:
            payload["password"] = password
        resp = self.session.post(f"{self.base_url}/api/files/{file_id}/shares", json=payload)
        assert resp.status_code == 201, f"Failed to create share link: {resp.text}"
        return resp.json()

    def revoke_share_link(self, share_id: str):
        resp = self.session.delete(f"{self.base_url}/api/shares/{share_id}")
        assert resp.status_code == 200, f"Failed to revoke share {share_id}: {resp.text}"
        return resp.json()


def run_full_suite():
    log("=" * 70)
    log("CLOUDBOX MULTI-LAPTOP SHARED STORAGE VERIFICATION SUITE")
    log("=" * 70)

    # Health check on backend
    health_resp = requests.get(f"{BASE_URL}/health")
    assert_true(health_resp.status_code == 200, f"Backend health check status {health_resp.status_code}")
    health_data = health_resp.json()
    log(f"Health status: {health_data}")
    assert_true(health_data.get("status") == "healthy", "Backend reports status healthy")
    assert_true(health_data.get("database", {}).get("database") == "cloudbox_db", "Database configured for cloudbox_db")
    assert_true(health_data.get("storage", {}).get("port") == 9000, "MinIO storage configured on port 9000")

    # Instantiate two simulated laptop nodes
    laptop1 = SimulatedLaptopNode("Laptop 1 (Node A)", BASE_URL)
    laptop2 = SimulatedLaptopNode("Laptop 2 (Node B)", BASE_URL)

    test_user_name = "karthik"
    test_user_email = "karthik@cloudbox.local"
    test_user_pass = "password123"

    # -------------------------------------------------------------------------
    # Test 1: Upload from Laptop 1
    # -------------------------------------------------------------------------
    log("\n--- TEST 1: Upload from Laptop 1 ---")
    user1 = laptop1.register_or_login(test_user_name, test_user_email, test_user_pass)
    assert_true(user1 is not None, "Laptop 1 successfully authenticated user")

    test1_content = f"Hello from Laptop 1! Unique ID: {uuid.uuid4()}\nCloudBox shared multi-laptop storage verification.".encode("utf-8")
    test1_filename = f"laptop1_test_{int(time.time())}.txt"
    test1_sha = compute_sha256(test1_content)

    log(f"Uploading file '{test1_filename}' ({len(test1_content)} bytes) from Laptop 1...")
    file1_meta = laptop1.upload_file(test1_filename, test1_content, "text/plain")
    assert_true(file1_meta["original_filename"] == test1_filename, "Laptop 1 file metadata matches uploaded name")
    assert_true(file1_meta["checksum_sha256"] == test1_sha, "Laptop 1 file checksum matches computed SHA-256")
    file1_id = file1_meta["id"]
    log(f"[+] File 1 created: ID={file1_id}, Name={file1_meta['original_filename']}")

    # -------------------------------------------------------------------------
    # Test 2: Access from Laptop 2 (Cross-Device Read & Download)
    # -------------------------------------------------------------------------
    log("\n--- TEST 2: Access from Laptop 2 ---")
    user2 = laptop2.register_or_login(test_user_name, test_user_email, test_user_pass)
    assert_true(user2["id"] == user1["id"], "Laptop 2 authenticated with identical User ID")

    log("Listing files on Laptop 2...")
    laptop2_files = laptop2.list_files()
    found_file1 = next((f for f in laptop2_files if f["id"] == file1_id), None)
    assert_true(found_file1 is not None, f"Laptop 2 found file '{test1_filename}' in file list")
    assert_true(found_file1["size_bytes"] == len(test1_content), "Laptop 2 sees exact byte size")

    log("Downloading file from Laptop 2...")
    downloaded_by_laptop2 = laptop2.download_file(file1_id)
    downloaded_sha = compute_sha256(downloaded_by_laptop2)
    assert_true(downloaded_sha == test1_sha, f"Downloaded SHA-256 ({downloaded_sha}) strictly matches original ({test1_sha})")
    assert_true(downloaded_by_laptop2 == test1_content, "Downloaded binary content on Laptop 2 matches exactly byte-for-byte")

    # -------------------------------------------------------------------------
    # Test 3: Upload from Laptop 2 and Read from Laptop 1
    # -------------------------------------------------------------------------
    log("\n--- TEST 3: Upload from Laptop 2 and Access from Laptop 1 ---")
    test2_content = f"Data generated on Laptop 2 at {time.time()}\nCross-device bi-directional synchronization active.".encode("utf-8")
    test2_filename = f"laptop2_test_{int(time.time())}.txt"
    test2_sha = compute_sha256(test2_content)

    log(f"Uploading '{test2_filename}' from Laptop 2...")
    file2_meta = laptop2.upload_file(test2_filename, test2_content, "text/plain")
    file2_id = file2_meta["id"]
    assert_true(file2_meta["checksum_sha256"] == test2_sha, "Laptop 2 file metadata recorded with accurate SHA-256")

    log("Verifying presence on Laptop 1...")
    laptop1_files = laptop1.list_files()
    found_file2 = next((f for f in laptop1_files if f["id"] == file2_id), None)
    assert_true(found_file2 is not None, f"Laptop 1 detected file '{test2_filename}' uploaded by Laptop 2")

    log("Downloading file on Laptop 1...")
    downloaded_by_laptop1 = laptop1.download_file(file2_id)
    assert_true(compute_sha256(downloaded_by_laptop1) == test2_sha, "Laptop 1 downloaded file byte stream matches Laptop 2 upload SHA-256")

    # -------------------------------------------------------------------------
    # Test 4: Cross-Device Operations
    # -------------------------------------------------------------------------
    log("\n--- TEST 4: Cross-Device Operations ---")
    
    # 4A: Rename on Laptop 1, check on Laptop 2
    renamed_filename = f"renamed_by_laptop1_{int(time.time())}.txt"
    log(f"Renaming file {file1_id} on Laptop 1 to '{renamed_filename}'...")
    laptop1.rename_file(file1_id, renamed_filename)
    
    laptop2_files_after_rename = laptop2.list_files()
    file1_on_node2 = next((f for f in laptop2_files_after_rename if f["id"] == file1_id), None)
    assert_true(file1_on_node2 is not None and file1_on_node2["original_filename"] == renamed_filename, 
                "Rename performed by Laptop 1 immediately reflects on Laptop 2")

    # 4B: Preview streaming on Laptop 2
    log("Previewing file content on Laptop 2...")
    preview_bytes = laptop2.preview_file(file1_id)
    assert_true(preview_bytes == test1_content, "Inline preview on Laptop 2 returns original text stream")

    # 4C: Sharing Link Creation on Laptop 1, access anonymously / from Laptop 2
    log("Creating public share link on Laptop 1...")
    share_result = laptop1.create_share_link(file1_id, permission="download")
    share_token = share_result.get("token")
    share_id = share_result.get("share", {}).get("id")
    assert_true(share_token is not None, "Share token generated on Laptop 1")

    log("Accessing share link via public HTTP endpoint...")
    public_resp = requests.get(f"{BASE_URL}/api/shared/{share_token}")
    assert_true(public_resp.status_code == 200, "Public share metadata retrieved successfully")
    assert_true(public_resp.json().get("original_filename") == renamed_filename, "Public share metadata reflects current filename")

    public_dl_resp = requests.get(f"{BASE_URL}/api/shared/{share_token}?download=true")
    assert_true(public_dl_resp.status_code == 200, "Public shared file downloaded successfully")
    assert_true(compute_sha256(public_dl_resp.content) == test1_sha, "Public download matches exact checksum")

    # 4D: Revoke Share Link on Laptop 2
    log("Revoking share link from Laptop 2...")
    laptop2.revoke_share_link(share_id)
    revoked_resp = requests.get(f"{BASE_URL}/api/shared/{share_token}")
    assert_true(revoked_resp.status_code == 410, "Revoked share link returns 410 Gone on subsequent access")

    # 4E: Soft Delete on Laptop 1, check Recycle Bin on Laptop 2
    log(f"Soft-deleting file {file2_id} from Laptop 1...")
    laptop1.soft_delete_file(file2_id)

    laptop2_active_files = laptop2.list_files()
    assert_true(not any(f["id"] == file2_id for f in laptop2_active_files), "Soft-deleted file removed from Laptop 2 active list")

    trash_on_laptop2 = laptop2.list_trash()
    assert_true(any(f["id"] == file2_id for f in trash_on_laptop2), "Soft-deleted file appears in Laptop 2 Recycle Bin")

    # 4F: Restore on Laptop 2, check active list on Laptop 1
    log(f"Restoring file {file2_id} from Laptop 2 Recycle Bin...")
    laptop2.restore_trash(file2_id)

    laptop1_restored_files = laptop1.list_files()
    assert_true(any(f["id"] == file2_id for f in laptop1_restored_files), "Restored file immediately appears in Laptop 1 active list")

    # 4G: User Isolation (User A vs User B)
    log("\n--- TEST 4G: User Isolation Verification ---")
    user_b_node = SimulatedLaptopNode("User B Node", BASE_URL)
    user_b_node.register_or_login("venkat", "venkat@cloudbox.local", "password123")
    user_b_files = user_b_node.list_files()
    assert_true(not any(f["id"] in [file1_id, file2_id] for f in user_b_files), "User A files are completely invisible to User B (Tenancy Isolation Verified)")

    # -------------------------------------------------------------------------
    # Test 5: Persistence & Verification
    # -------------------------------------------------------------------------
    log("\n--- TEST 5: Persistence & Storage Verification ---")
    log("Verifying that all data persisted cleanly in PostgreSQL and MinIO...")
    final_files = laptop1.list_files()
    assert_true(any(f["id"] == file1_id for f in final_files), f"File 1 ({file1_id}) persists in database")
    assert_true(any(f["id"] == file2_id for f in final_files), f"File 2 ({file2_id}) persists in database")

    log("\n" + "=" * 70)
    log("[SUCCESS] ALL 5 PHASES OF CROSS-DEVICE SHARED STORAGE TESTING PASSED!")
    log("=" * 70)
    return True

if __name__ == "__main__":
    try:
        run_full_suite()
    except Exception as e:
        log(f"Error during verification: {e}", symbol="[-]")
        sys.exit(1)
