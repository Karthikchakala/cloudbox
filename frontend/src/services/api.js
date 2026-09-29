const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:5000';

export function getAuthToken() {
  return localStorage.getItem('cloudbox_token');
}

export function setAuthToken(token) {
  if (token) {
    localStorage.setItem('cloudbox_token', token);
  } else {
    localStorage.removeItem('cloudbox_token');
  }
}

function getHeaders(customHeaders = {}) {
  const token = getAuthToken();
  const headers = { ...customHeaders };
  if (token) {
    headers['Authorization'] = `Bearer ${token}`;
  }
  return headers;
}

// ---------------------------------------------------------------------------
// Health & Auth
// ---------------------------------------------------------------------------

export async function getBackendHealth() {
  try {
    const res = await fetch(`${API_BASE_URL}/health`);
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const data = await res.json();
    return { ok: true, data };
  } catch (error) {
    return { ok: false, error: error.message || 'Failed to connect to backend' };
  }
}

export async function registerUser(username, email, password) {
  try {
    const res = await fetch(`${API_BASE_URL}/api/auth/register`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ username, email, password }),
    });
    const data = await res.json();
    if (!res.ok) return { ok: false, error: data.error || 'Registration failed' };
    if (data.access_token) setAuthToken(data.access_token);
    return { ok: true, data };
  } catch (error) {
    return { ok: false, error: error.message || 'Network error during registration' };
  }
}

export async function loginUser(email, password) {
  try {
    const res = await fetch(`${API_BASE_URL}/api/auth/login`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ email, password }),
    });
    const data = await res.json();
    if (!res.ok) return { ok: false, error: data.error || 'Invalid email or password' };
    if (data.access_token) setAuthToken(data.access_token);
    return { ok: true, data };
  } catch (error) {
    return { ok: false, error: error.message || 'Network error during login' };
  }
}

export async function getCurrentUser() {
  try {
    const token = getAuthToken();
    if (!token) return { ok: false, error: 'No token' };

    const res = await fetch(`${API_BASE_URL}/api/auth/me`, {
      headers: getHeaders(),
    });
    const data = await res.json();
    if (!res.ok) {
      if (res.status === 401) setAuthToken(null);
      return { ok: false, error: data.error || 'Unauthorized' };
    }
    return { ok: true, data: data.user };
  } catch (error) {
    return { ok: false, error: error.message || 'Failed to fetch user' };
  }
}

// ---------------------------------------------------------------------------
// File Management (Active)
// ---------------------------------------------------------------------------

export async function listFiles(page = 1, perPage = 20, search = '') {
  try {
    const params = new URLSearchParams({ page: page.toString(), per_page: perPage.toString() });
    if (search) params.append('search', search);

    const res = await fetch(`${API_BASE_URL}/api/files?${params.toString()}`, {
      headers: getHeaders(),
    });
    const data = await res.json();
    if (!res.ok) return { ok: false, error: data.error || 'Failed to list files' };
    return { ok: true, data };
  } catch (error) {
    return { ok: false, error: error.message || 'Network error listing files' };
  }
}

export async function uploadFile(file) {
  try {
    const formData = new FormData();
    formData.append('file', file);

    const res = await fetch(`${API_BASE_URL}/api/files`, {
      method: 'POST',
      headers: getHeaders(),
      body: formData,
    });
    const data = await res.json();
    if (!res.ok) return { ok: false, error: data.error || 'Upload failed' };
    return { ok: true, data: data.file };
  } catch (error) {
    return { ok: false, error: error.message || 'Network error during upload' };
  }
}

export async function downloadFile(fileId, filename) {
  try {
    const res = await fetch(`${API_BASE_URL}/api/files/${fileId}/download`, {
      headers: getHeaders(),
    });
    if (!res.ok) {
      const errorData = await res.json().catch(() => ({}));
      return { ok: false, error: errorData.error || `Download failed (HTTP ${res.status})` };
    }

    const blob = await res.blob();
    const url = window.URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = filename;
    document.body.appendChild(link);
    link.click();
    link.remove();
    window.URL.revokeObjectURL(url);
    return { ok: true };
  } catch (error) {
    return { ok: false, error: error.message || 'Network error during download' };
  }
}

export async function deleteFile(fileId) {
  try {
    const res = await fetch(`${API_BASE_URL}/api/files/${fileId}`, {
      method: 'DELETE',
      headers: getHeaders(),
    });
    const data = await res.json();
    if (!res.ok) return { ok: false, error: data.error || 'Delete failed' };
    return { ok: true, data };
  } catch (error) {
    return { ok: false, error: error.message || 'Network error during deletion' };
  }
}

// ---------------------------------------------------------------------------
// FEATURE A: File Versioning
// ---------------------------------------------------------------------------

export async function listVersions(fileId) {
  try {
    const res = await fetch(`${API_BASE_URL}/api/files/${fileId}/versions`, {
      headers: getHeaders(),
    });
    const data = await res.json();
    if (!res.ok) return { ok: false, error: data.error || 'Failed to list versions' };
    return { ok: true, data };
  } catch (error) {
    return { ok: false, error: error.message || 'Network error listing versions' };
  }
}

export async function uploadNewVersion(fileId, file) {
  try {
    const formData = new FormData();
    formData.append('file', file);

    const res = await fetch(`${API_BASE_URL}/api/files/${fileId}/versions`, {
      method: 'POST',
      headers: getHeaders(),
      body: formData,
    });
    const data = await res.json();
    if (!res.ok) return { ok: false, error: data.error || 'Failed to upload version' };
    return { ok: true, data };
  } catch (error) {
    return { ok: false, error: error.message || 'Network error uploading version' };
  }
}

export async function downloadVersion(fileId, versionId, filename) {
  try {
    const res = await fetch(`${API_BASE_URL}/api/files/${fileId}/versions/${versionId}/download`, {
      headers: getHeaders(),
    });
    if (!res.ok) {
      const errorData = await res.json().catch(() => ({}));
      return { ok: false, error: errorData.error || 'Download version failed' };
    }

    const blob = await res.blob();
    const url = window.URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = filename;
    document.body.appendChild(link);
    link.click();
    link.remove();
    window.URL.revokeObjectURL(url);
    return { ok: true };
  } catch (error) {
    return { ok: false, error: error.message || 'Network error downloading version' };
  }
}

export async function restoreVersion(fileId, versionId) {
  try {
    const res = await fetch(`${API_BASE_URL}/api/files/${fileId}/versions/${versionId}/restore`, {
      method: 'POST',
      headers: getHeaders(),
    });
    const data = await res.json();
    if (!res.ok) return { ok: false, error: data.error || 'Restore failed' };
    return { ok: true, data };
  } catch (error) {
    return { ok: false, error: error.message || 'Network error restoring version' };
  }
}

export async function deleteVersion(fileId, versionId) {
  try {
    const res = await fetch(`${API_BASE_URL}/api/files/${fileId}/versions/${versionId}`, {
      method: 'DELETE',
      headers: getHeaders(),
    });
    const data = await res.json();
    if (!res.ok) return { ok: false, error: data.error || 'Delete version failed' };
    return { ok: true, data };
  } catch (error) {
    return { ok: false, error: error.message || 'Network error deleting version' };
  }
}

// ---------------------------------------------------------------------------
// FEATURE B: Sharing Links
// ---------------------------------------------------------------------------

export async function createShareLink(fileId, options = {}) {
  try {
    const res = await fetch(`${API_BASE_URL}/api/files/${fileId}/shares`, {
      method: 'POST',
      headers: getHeaders({ 'Content-Type': 'application/json' }),
      body: JSON.stringify(options),
    });
    const data = await res.json();
    if (!res.ok) return { ok: false, error: data.error || 'Failed to create share link' };
    return { ok: true, data };
  } catch (error) {
    return { ok: false, error: error.message || 'Network error creating share link' };
  }
}

export async function listShareLinks(fileId) {
  try {
    const res = await fetch(`${API_BASE_URL}/api/files/${fileId}/shares`, {
      headers: getHeaders(),
    });
    const data = await res.json();
    if (!res.ok) return { ok: false, error: data.error || 'Failed to list share links' };
    return { ok: true, data };
  } catch (error) {
    return { ok: false, error: error.message || 'Network error listing share links' };
  }
}

export async function revokeShareLink(shareId) {
  try {
    const res = await fetch(`${API_BASE_URL}/api/shares/${shareId}`, {
      method: 'DELETE',
      headers: getHeaders(),
    });
    const data = await res.json();
    if (!res.ok) return { ok: false, error: data.error || 'Failed to revoke share link' };
    return { ok: true, data };
  } catch (error) {
    return { ok: false, error: error.message || 'Network error revoking share link' };
  }
}

export async function getSharedFileInfo(token, password = null) {
  try {
    const headers = {};
    if (password) headers['X-Share-Password'] = password;

    const res = await fetch(`${API_BASE_URL}/api/shared/${token}`, { headers });
    const data = await res.json();
    if (!res.ok) return { ok: false, status: res.status, error: data.error || 'Invalid or expired share link' };
    return { ok: true, data };
  } catch (error) {
    return { ok: false, error: error.message || 'Network error accessing share link' };
  }
}

export async function downloadSharedFile(token, password = null, filename = 'downloaded_file') {
  try {
    const headers = {};
    if (password) headers['X-Share-Password'] = password;

    const res = await fetch(`${API_BASE_URL}/api/shared/${token}?download=true`, { headers });
    if (!res.ok) {
      const errData = await res.json().catch(() => ({}));
      return { ok: false, status: res.status, error: errData.error || 'Download failed' };
    }

    const blob = await res.blob();
    const url = window.URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = filename;
    document.body.appendChild(link);
    link.click();
    link.remove();
    window.URL.revokeObjectURL(url);
    return { ok: true };
  } catch (error) {
    return { ok: false, error: error.message || 'Network error downloading shared file' };
  }
}

export async function verifySharedPassword(token, password) {
  try {
    const res = await fetch(`${API_BASE_URL}/api/shared/${token}/verify`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ password }),
    });
    const data = await res.json();
    if (!res.ok) return { ok: false, error: data.error || 'Incorrect password' };
    return { ok: true, data };
  } catch (error) {
    return { ok: false, error: error.message || 'Network error verifying password' };
  }
}

// ---------------------------------------------------------------------------
// FEATURE C: Recycle Bin
// ---------------------------------------------------------------------------

export async function listTrash() {
  try {
    const res = await fetch(`${API_BASE_URL}/api/trash`, {
      headers: getHeaders(),
    });
    const data = await res.json();
    if (!res.ok) return { ok: false, error: data.error || 'Failed to list trash' };
    return { ok: true, data };
  } catch (error) {
    return { ok: false, error: error.message || 'Network error listing trash' };
  }
}

export async function restoreFromTrash(fileId) {
  try {
    const res = await fetch(`${API_BASE_URL}/api/trash/${fileId}/restore`, {
      method: 'POST',
      headers: getHeaders(),
    });
    const data = await res.json();
    if (!res.ok) return { ok: false, error: data.error || 'Failed to restore file' };
    return { ok: true, data };
  } catch (error) {
    return { ok: false, error: error.message || 'Network error restoring file' };
  }
}

export async function permanentDeleteFile(fileId) {
  try {
    const res = await fetch(`${API_BASE_URL}/api/trash/${fileId}`, {
      method: 'DELETE',
      headers: getHeaders(),
    });
    const data = await res.json();
    if (!res.ok) return { ok: false, error: data.error || 'Failed to permanently delete file' };
    return { ok: true, data };
  } catch (error) {
    return { ok: false, error: error.message || 'Network error during permanent deletion' };
  }
}

export async function emptyTrash() {
  try {
    const res = await fetch(`${API_BASE_URL}/api/trash`, {
      method: 'DELETE',
      headers: getHeaders(),
    });
    const data = await res.json();
    if (!res.ok) return { ok: false, error: data.error || 'Failed to empty recycle bin' };
    return { ok: true, data };
  } catch (error) {
    return { ok: false, error: error.message || 'Network error emptying recycle bin' };
  }
}

// ---------------------------------------------------------------------------
// Analytics & Metrics (Phase 4)
// ---------------------------------------------------------------------------

export async function getAnalyticsOverview() {
  try {
    const res = await fetch(`${API_BASE_URL}/api/analytics/overview`, {
      headers: getHeaders(),
    });
    const data = await res.json();
    if (!res.ok) return { ok: false, error: data.error || 'Failed to load storage analytics' };
    return { ok: true, data };
  } catch (error) {
    return { ok: false, error: error.message || 'Network error fetching analytics' };
  }
}

// ---------------------------------------------------------------------------
// Chunked Uploads & Processing (Phase 5)
// ---------------------------------------------------------------------------

export async function initiateChunkedUpload(filename, fileSize, contentType, chunkSize = 5 * 1024 * 1024, targetFileId = null) {
  try {
    const res = await fetch(`${API_BASE_URL}/api/uploads/initiate`, {
      method: 'POST',
      headers: getHeaders({ 'Content-Type': 'application/json' }),
      body: JSON.stringify({
        filename,
        file_size: fileSize,
        content_type: contentType,
        chunk_size: chunkSize,
        target_file_id: targetFileId,
      }),
    });
    const data = await res.json();
    if (!res.ok) return { ok: false, error: data.error || 'Failed to initiate chunked upload' };
    return { ok: true, data };
  } catch (error) {
    return { ok: false, error: error.message || 'Network error initiating upload' };
  }
}

export async function uploadChunkPart(uploadId, chunkNumber, chunkBlob) {
  try {
    const res = await fetch(`${API_BASE_URL}/api/uploads/${uploadId}/chunks/${chunkNumber}`, {
      method: 'PUT',
      headers: getHeaders({ 'Content-Type': 'application/octet-stream' }),
      body: chunkBlob,
    });
    const data = await res.json();
    if (!res.ok) return { ok: false, error: data.error || `Failed uploading chunk ${chunkNumber}` };
    return { ok: true, data };
  } catch (error) {
    return { ok: false, error: error.message || `Network error uploading chunk ${chunkNumber}` };
  }
}

export async function getUploadSessionStatus(uploadId) {
  try {
    const res = await fetch(`${API_BASE_URL}/api/uploads/${uploadId}`, {
      headers: getHeaders(),
    });
    const data = await res.json();
    if (!res.ok) return { ok: false, error: data.error || 'Failed to check upload status' };
    return { ok: true, data: data.session };
  } catch (error) {
    return { ok: false, error: error.message || 'Network error checking upload status' };
  }
}

export async function completeChunkedUpload(uploadId) {
  try {
    const res = await fetch(`${API_BASE_URL}/api/uploads/${uploadId}/complete`, {
      method: 'POST',
      headers: getHeaders(),
    });
    const data = await res.json();
    if (!res.ok) return { ok: false, error: data.error || 'Failed to complete chunk assembly' };
    return { ok: true, data };
  } catch (error) {
    return { ok: false, error: error.message || 'Network error completing upload' };
  }
}

export async function cancelChunkedUpload(uploadId) {
  try {
    const res = await fetch(`${API_BASE_URL}/api/uploads/${uploadId}`, {
      method: 'DELETE',
      headers: getHeaders(),
    });
    const data = await res.json();
    if (!res.ok) return { ok: false, error: data.error || 'Failed to cancel upload' };
    return { ok: true, data };
  } catch (error) {
    return { ok: false, error: error.message || 'Network error cancelling upload' };
  }
}

export async function getFileProcessingStatus(fileId) {
  try {
    const res = await fetch(`${API_BASE_URL}/api/files/${fileId}/processing-status`, {
      headers: getHeaders(),
    });
    const data = await res.json();
    if (!res.ok) return { ok: false, error: data.error || 'Failed to fetch processing status' };
    return { ok: true, data };
  } catch (error) {
    return { ok: false, error: error.message || 'Network error fetching processing status' };
  }
}

export async function fetchFileThumbnailBlob(fileId) {
  try {
    const res = await fetch(`${API_BASE_URL}/api/files/${fileId}/thumbnail`, {
      headers: getHeaders(),
    });
    if (!res.ok) return { ok: false };
    const blob = await res.blob();
    return { ok: true, blobUrl: URL.createObjectURL(blob) };
  } catch (error) {
    return { ok: false };
  }
}

export async function fetchFilePreviewBlob(fileId) {
  try {
    const res = await fetch(`${API_BASE_URL}/api/files/${fileId}/preview`, {
      headers: getHeaders(),
    });
    if (!res.ok) return { ok: false, error: 'Preview not available' };
    const blob = await res.blob();
    const contentType = res.headers.get('Content-Type') || blob.type || 'application/octet-stream';
    let textContent = null;
    if (
      contentType.startsWith('text/') ||
      contentType.includes('json') ||
      contentType.includes('javascript') ||
      contentType.includes('xml') ||
      contentType.includes('yaml') ||
      contentType.includes('sql')
    ) {
      try {
        textContent = await blob.text();
      } catch (e) {
        textContent = null;
      }
    }
    return {
      ok: true,
      blob,
      blobUrl: URL.createObjectURL(blob),
      contentType,
      textContent,
    };
  } catch (error) {
    return { ok: false, error: error.message };
  }
}

export async function getSystemMetrics() {
  try {
    const res = await fetch(`${API_BASE_URL}/api/metrics`);
    const data = await res.json();
    if (!res.ok) return { ok: false, error: 'Failed to load system metrics' };
    return { ok: true, data };
  } catch (error) {
    return { ok: false, error: error.message };
  }
}


