"""
Comprehensive Phase 3 File Management & Security Isolation Test Suite
"""
import requests
import hashlib
import io
import time

BASE_URL = "http://localhost:5000/api"

def login(username, password="password123"):
    res = requests.post(f"{BASE_URL}/auth/login", json={"username": username, "password": password})
    assert res.status_code == 200, f"Login failed for {username}: {res.text}"
    return res.json()["access_token"]

def run_phase3_suite():
    print("==================================================")
    print("PHASE 3: COMPREHENSIVE FILE MANAGEMENT & SECURITY")
    print("==================================================")

    token_karthik = login("karthik")
    token_venkat = login("venkat")
    headers_karthik = {"Authorization": f"Bearer {token_karthik}"}
    headers_venkat = {"Authorization": f"Bearer {token_venkat}"}

    # 1. Text File Upload
    text_data = b"Hello CloudBox! Enterprise Document Content for Karthik."
    text_sha = hashlib.sha256(text_data).hexdigest()
    r_txt = requests.post(
        f"{BASE_URL}/files",
        headers=headers_karthik,
        files={"file": ("project_spec.txt", io.BytesIO(text_data), "text/plain")}
    )
    assert r_txt.status_code == 201, f"Text upload failed: {r_txt.text}"
    txt_file = r_txt.json()["file"]
    txt_id = txt_file["id"]
    print(f"[PASS] Uploaded Text File: 'project_spec.txt' (ID: {txt_id}, SHA: {text_sha[:8]}...)")

    # 2. PDF File Upload Simulation
    pdf_data = b"%PDF-1.4 CloudBox Architecture Diagram and Schema Design."
    pdf_sha = hashlib.sha256(pdf_data).hexdigest()
    r_pdf = requests.post(
        f"{BASE_URL}/files",
        headers=headers_karthik,
        files={"file": ("architecture_v1.pdf", io.BytesIO(pdf_data), "application/pdf")}
    )
    assert r_pdf.status_code == 201
    pdf_id = r_pdf.json()["file"]["id"]
    print(f"[PASS] Uploaded PDF File: 'architecture_v1.pdf' (ID: {pdf_id})")

    # 3. Image File Upload Simulation
    img_data = b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06\x00\x00\x00\x1f\x15c4\x00\x00\x00\nIDATx\x9cc\x00\x01\x00\x00\x05\x00\x01\r\n-\xb4\x00\x00\x00\x00IEND\xaeB`\x82"
    r_img = requests.post(
        f"{BASE_URL}/files",
        headers=headers_karthik,
        files={"file": ("cloudbox_icon.png", io.BytesIO(img_data), "image/png")}
    )
    assert r_img.status_code == 201
    img_id = r_img.json()["file"]["id"]
    print(f"[PASS] Uploaded Image File: 'cloudbox_icon.png' (ID: {img_id})")

    # 4. Special Characters & Spaces
    spec_data = b"Testing special filenames & symbols [2026]!"
    r_spec = requests.post(
        f"{BASE_URL}/files",
        headers=headers_karthik,
        files={"file": ("My Report #2026 (v1.0) & Final.txt", io.BytesIO(spec_data), "text/plain")}
    )
    assert r_spec.status_code == 201
    spec_id = r_spec.json()["file"]["id"]
    print(f"[PASS] Uploaded File with Special Characters: 'My Report #2026 (v1.0) & Final.txt' (ID: {spec_id})")

    # 5. Empty File Rejection
    r_empty = requests.post(
        f"{BASE_URL}/files",
        headers=headers_karthik,
        files={"file": ("empty.txt", io.BytesIO(b""), "text/plain")}
    )
    assert r_empty.status_code == 400
    print("[PASS] Empty file upload rejected with HTTP 400.")

    # 6. File Download & Checksum Verification
    r_down = requests.get(f"{BASE_URL}/files/{txt_id}/download", headers=headers_karthik)
    assert r_down.status_code == 200
    assert hashlib.sha256(r_down.content).hexdigest() == text_sha
    print("[PASS] File download verified with exact SHA256 match.")

    # 7. File Rename
    r_ren = requests.patch(f"{BASE_URL}/files/{txt_id}", headers=headers_karthik, json={"name": "project_spec_renamed.txt"})
    assert r_ren.status_code == 200
    assert r_ren.json()["file"]["original_filename"] == "project_spec_renamed.txt"
    print("[PASS] File renamed to 'project_spec_renamed.txt'")

    # 8. File Versioning (Upload Version 2)
    v2_data = b"Updated Spec Content - Version 2."
    r_v2 = requests.post(
        f"{BASE_URL}/files/{txt_id}/versions",
        headers=headers_karthik,
        files={"file": ("project_spec_renamed.txt", io.BytesIO(v2_data), "text/plain")}
    )
    assert r_v2.status_code == 201
    print("[PASS] Version 2 created successfully.")

    # Verify Version 2 Download
    r_down_v2 = requests.get(f"{BASE_URL}/files/{txt_id}/download", headers=headers_karthik)
    assert r_down_v2.content == v2_data
    print("[PASS] Download active file returns Version 2 content.")

    # 9. Share Link Creation & Public Access
    r_share = requests.post(
        f"{BASE_URL}/files/{txt_id}/shares",
        headers=headers_karthik,
        json={"permission": "download"}
    )
    assert r_share.status_code == 201, f"Share creation failed: {r_share.text}"
    share_token = r_share.json()["token"]
    print(f"[PASS] Created public share link (Token: {share_token[:10]}...)")

    r_pub_down = requests.get(f"{BASE_URL}/shared/{share_token}?download=true")
    assert r_pub_down.status_code == 200, f"Public download failed: {r_pub_down.text}"
    assert r_pub_down.content == v2_data
    print("[PASS] Public share link download verified successfully.")

    # 10. Cross-User Security Isolation (Venkat vs Karthik)
    r_iso_get = requests.get(f"{BASE_URL}/files/{txt_id}", headers=headers_venkat)
    assert r_iso_get.status_code == 404, f"Expected 404, got {r_iso_get.status_code}"
    r_iso_down = requests.get(f"{BASE_URL}/files/{txt_id}/download", headers=headers_venkat)
    assert r_iso_down.status_code == 404
    r_iso_del = requests.delete(f"{BASE_URL}/files/{txt_id}", headers=headers_venkat)
    assert r_iso_del.status_code == 404
    print("[PASS] User isolation confirmed: venkat cannot read, download, or delete karthik's files.")

    # 11. Recycle Bin (Soft Delete, List, Restore)
    r_del = requests.delete(f"{BASE_URL}/files/{img_id}", headers=headers_karthik)
    assert r_del.status_code == 200
    print("[PASS] Moved 'cloudbox_icon.png' to Recycle Bin.")

    r_trash = requests.get(f"{BASE_URL}/trash", headers=headers_karthik)
    assert r_trash.status_code == 200
    trash_ids = [f["id"] for f in r_trash.json().get("files", [])]
    assert img_id in trash_ids
    print("[PASS] File listed in Recycle Bin.")

    r_restore = requests.post(f"{BASE_URL}/trash/{img_id}/restore", headers=headers_karthik)
    assert r_restore.status_code == 200
    print("[PASS] Restored file from Recycle Bin.")

    # 12. Nonexistent File Handling
    r_nonexist = requests.get(f"{BASE_URL}/files/00000000-0000-0000-0000-000000000000", headers=headers_karthik)
    assert r_nonexist.status_code == 404
    print("[PASS] Nonexistent file lookup returns HTTP 404.")

    print("\n>>> ALL PHASE 3 FILE MANAGEMENT & SECURITY TESTS PASSED (100%) <<<")

if __name__ == "__main__":
    run_phase3_suite()
