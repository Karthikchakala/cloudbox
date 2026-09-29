import io

def test_soft_delete_and_list_trash(client, auth_headers):
    """Test soft delete moves file to trash and hides from normal listing."""
    res = client.post(
        "/api/files",
        data={"file": (io.BytesIO(b"Data to be trashed"), "trash_test.txt")},
        content_type="multipart/form-data",
        headers=auth_headers
    )
    file_id = res.get_json()["file"]["id"]

    # Verify visible in normal file listing
    active_res1 = client.get("/api/files", headers=auth_headers)
    assert len(active_res1.get_json()["files"]) == 1

    # Soft delete
    del_res = client.delete(f"/api/files/{file_id}", headers=auth_headers)
    assert del_res.status_code == 200

    # Verify hidden from normal file listing
    active_res2 = client.get("/api/files", headers=auth_headers)
    assert len(active_res2.get_json()["files"]) == 0

    # Verify present in trash listing
    trash_res = client.get("/api/trash", headers=auth_headers)
    assert trash_res.status_code == 200
    assert len(trash_res.get_json()["files"]) == 1
    assert trash_res.get_json()["files"][0]["id"] == file_id

def test_restore_file_from_trash(client, auth_headers):
    """Test restoring a file returns it to active file catalog with versions."""
    res = client.post(
        "/api/files",
        data={"file": (io.BytesIO(b"Important Document v1"), "restore_me.txt")},
        content_type="multipart/form-data",
        headers=auth_headers
    )
    file_id = res.get_json()["file"]["id"]

    # Add v2
    client.post(
        f"/api/files/{file_id}/versions",
        data={"file": (io.BytesIO(b"Important Document v2"), "restore_me.txt")},
        content_type="multipart/form-data",
        headers=auth_headers
    )

    # Move to trash
    client.delete(f"/api/files/{file_id}", headers=auth_headers)

    # Restore from trash
    rest_res = client.post(f"/api/trash/{file_id}/restore", headers=auth_headers)
    assert rest_res.status_code == 200

    # Verify now back in active file listing
    active_res = client.get("/api/files", headers=auth_headers)
    assert len(active_res.get_json()["files"]) == 1

    # Verify version history remains intact
    ver_res = client.get(f"/api/files/{file_id}/versions", headers=auth_headers)
    assert len(ver_res.get_json()["versions"]) == 2

def test_permanent_delete_file(client, auth_headers):
    """Test permanently deleting a file removes it completely."""
    res = client.post(
        "/api/files",
        data={"file": (io.BytesIO(b"Temporary Data"), "perm_del.txt")},
        content_type="multipart/form-data",
        headers=auth_headers
    )
    file_id = res.get_json()["file"]["id"]

    # Soft delete
    client.delete(f"/api/files/{file_id}", headers=auth_headers)

    # Permanent delete
    perm_res = client.delete(f"/api/trash/{file_id}", headers=auth_headers)
    assert perm_res.status_code == 200

    # Verify gone from trash
    trash_res = client.get("/api/trash", headers=auth_headers)
    assert len(trash_res.get_json()["files"]) == 0

    # Verify 404 on restore attempt
    assert client.post(f"/api/trash/{file_id}/restore", headers=auth_headers).status_code == 404

def test_empty_recycle_bin(client, auth_headers):
    """Test emptying entire recycle bin."""
    # Upload 2 files
    res1 = client.post("/api/files", data={"file": (io.BytesIO(b"Trash 1"), "t1.txt")}, content_type="multipart/form-data", headers=auth_headers)
    res2 = client.post("/api/files", data={"file": (io.BytesIO(b"Trash 2"), "t2.txt")}, content_type="multipart/form-data", headers=auth_headers)

    # Move both to trash
    client.delete(f"/api/files/{res1.get_json()['file']['id']}", headers=auth_headers)
    client.delete(f"/api/files/{res2.get_json()['file']['id']}", headers=auth_headers)

    assert len(client.get("/api/trash", headers=auth_headers).get_json()["files"]) == 2

    # Empty trash
    empty_res = client.delete("/api/trash", headers=auth_headers)
    assert empty_res.status_code == 200
    assert empty_res.get_json()["deleted_count"] == 2

    # Verify trash is now empty
    assert len(client.get("/api/trash", headers=auth_headers).get_json()["files"]) == 0

def test_cross_user_trash_isolation(client, auth_headers, second_auth_headers):
    """Test User 2 cannot access, restore, or delete User 1's trashed files."""
    res = client.post(
        "/api/files",
        data={"file": (io.BytesIO(b"User 1 Trashed File"), "u1_trash.txt")},
        content_type="multipart/form-data",
        headers=auth_headers
    )
    file_id = res.get_json()["file"]["id"]
    client.delete(f"/api/files/{file_id}", headers=auth_headers)

    # User 2 trash listing should be empty
    u2_trash = client.get("/api/trash", headers=second_auth_headers)
    assert len(u2_trash.get_json()["files"]) == 0

    # User 2 cannot restore User 1's file -> 404
    assert client.post(f"/api/trash/{file_id}/restore", headers=second_auth_headers).status_code == 404

    # User 2 cannot permanently delete User 1's file -> 404
    assert client.delete(f"/api/trash/{file_id}", headers=second_auth_headers).status_code == 404
