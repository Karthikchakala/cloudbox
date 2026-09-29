import React, { useState, useEffect, useRef } from 'react';
import { 
  UploadCloud, 
  File as FileIcon, 
  FileText, 
  Image as ImageIcon, 
  Film, 
  Music, 
  Archive, 
  Code, 
  Download, 
  Trash2, 
  Search, 
  RefreshCw, 
  CheckCircle2, 
  AlertCircle,
  HardDrive,
  Clock,
  Layers,
  GitBranch,
  Share2,
  Eye,
  Loader2,
  XCircle,
  Play,
  Pause
} from 'lucide-react';
import { 
  listFiles, 
  uploadFile, 
  downloadFile, 
  deleteFile, 
  initiateChunkedUpload, 
  uploadChunkPart, 
  completeChunkedUpload, 
  cancelChunkedUpload 
} from '../services/api';
import VersionModal from './VersionModal';
import ShareModal from './ShareModal';
import FilePreviewModal from './FilePreviewModal';

const CHUNK_SIZE = 5 * 1024 * 1024; // 5 MB chunks

export default function FileManager({ user, onOpenTrash }) {
  const [files, setFiles] = useState([]);
  const [pagination, setPagination] = useState({ page: 1, per_page: 20, total: 0, total_pages: 1 });
  const [search, setSearch] = useState('');
  const [loading, setLoading] = useState(true);
  const [uploadProgress, setUploadProgress] = useState(null); // { filename, totalChunks, currentChunk, percent, uploadId, active }
  const [toast, setToast] = useState(null);
  const [selectedVersionFile, setSelectedVersionFile] = useState(null);
  const [selectedShareFile, setSelectedShareFile] = useState(null);
  const [selectedPreviewFile, setSelectedPreviewFile] = useState(null);
  const [confirmTrashId, setConfirmTrashId] = useState(null);
  const fileInputRef = useRef(null);

  const showToast = (type, text) => {
    setToast({ type, text });
    setTimeout(() => setToast(null), 4500);
  };

  const fetchFileList = async (page = 1, searchQuery = search) => {
    setLoading(true);
    const res = await listFiles(page, 20, searchQuery);
    if (res.ok) {
      setFiles(res.data.files || []);
      setPagination(res.data.pagination || { page: 1, per_page: 20, total: 0, total_pages: 1 });
    } else {
      showToast('error', res.error);
    }
    setLoading(false);
  };

  useEffect(() => {
    fetchFileList(1, search);
  }, [user]);

  const handleSearchChange = (e) => {
    const val = e.target.value;
    setSearch(val);
    fetchFileList(1, val);
  };

  const handleFileUpload = async (fileObj) => {
    if (!fileObj) return;

    if (fileObj.size > 500 * 1024 * 1024) {
      showToast('error', 'File size exceeds maximum upload limit of 500 MB.');
      return;
    }

    // Use Chunked Multipart Upload for files > 5 MB
    if (fileObj.size > CHUNK_SIZE) {
      await performChunkedUpload(fileObj);
    } else {
      // Standard Single-Request Upload for smaller files
      setUploadProgress({ filename: fileObj.name, totalChunks: 1, currentChunk: 1, percent: 50, active: true });
      const res = await uploadFile(fileObj);
      if (res.ok) {
        showToast('success', `"${fileObj.name}" uploaded successfully (v1).`);
        fetchFileList(1, search);
      } else {
        showToast('error', res.error);
      }
      setUploadProgress(null);
    }

    if (fileInputRef.current) fileInputRef.current.value = '';
  };

  const performChunkedUpload = async (fileObj) => {
    const totalChunks = Math.ceil(fileObj.size / CHUNK_SIZE);
    setUploadProgress({
      filename: fileObj.name,
      totalChunks,
      currentChunk: 0,
      percent: 0,
      uploadId: null,
      active: true
    });

    // 1. Initiate upload session
    const initRes = await initiateChunkedUpload(fileObj.name, fileObj.size, fileObj.type || 'application/octet-stream', CHUNK_SIZE);
    if (!initRes.ok) {
      showToast('error', initRes.error || 'Failed to initiate chunked upload.');
      setUploadProgress(null);
      return;
    }

    const uploadId = initRes.data.upload_id;
    setUploadProgress((prev) => ({ ...prev, uploadId }));

    try {
      // 2. Upload chunks sequentially
      for (let chunkNumber = 1; chunkNumber <= totalChunks; chunkNumber++) {
        const start = (chunkNumber - 1) * CHUNK_SIZE;
        const end = Math.min(start + CHUNK_SIZE, fileObj.size);
        const chunkBlob = fileObj.slice(start, end);

        const chunkRes = await uploadChunkPart(uploadId, chunkNumber, chunkBlob);
        if (!chunkRes.ok) {
          throw new Error(chunkRes.error || `Error uploading chunk ${chunkNumber}`);
        }

        const percent = Math.round((chunkNumber / totalChunks) * 100);
        setUploadProgress((prev) => ({
          ...prev,
          currentChunk: chunkNumber,
          percent
        }));
      }

      // 3. Complete chunk assembly
      const compRes = await completeChunkedUpload(uploadId);
      if (compRes.ok) {
        showToast('success', `"${fileObj.name}" assembled and uploaded successfully.`);
        fetchFileList(1, search);
      } else {
        showToast('error', compRes.error || 'Failed completing chunked upload.');
      }
    } catch (err) {
      showToast('error', err.message || 'Chunked upload failed.');
      await cancelChunkedUpload(uploadId);
    } finally {
      setUploadProgress(null);
    }
  };

  const handleCancelCurrentUpload = async () => {
    if (uploadProgress?.uploadId) {
      await cancelChunkedUpload(uploadProgress.uploadId);
    }
    setUploadProgress(null);
    showToast('error', 'Upload cancelled.');
  };

  const handleDownload = async (file) => {
    showToast('success', `Downloading "${file.original_filename}"...`);
    const res = await downloadFile(file.id, file.original_filename);
    if (!res.ok) {
      showToast('error', res.error);
    }
  };

  const handleMoveToTrash = async (file) => {
    const res = await deleteFile(file.id);
    if (res.ok) {
      showToast('success', `"${file.original_filename}" moved to Recycle Bin.`);
      setFiles((prev) => prev.filter((f) => f.id !== file.id));
      setConfirmTrashId(null);
    } else {
      showToast('error', res.error);
    }
  };

  const formatBytes = (bytes) => {
    if (!bytes || bytes === 0) return '0 B';
    const k = 1024;
    const sizes = ['B', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
  };

  const getFileIcon = (contentType, filename) => {
    const ext = filename ? filename.split('.').pop().toLowerCase() : '';
    if (contentType?.startsWith('image/') || ['jpg', 'jpeg', 'png', 'svg', 'gif', 'webp'].includes(ext)) {
      return <ImageIcon size={20} color="#38bdf8" />;
    }
    if (contentType?.startsWith('video/') || ['mp4', 'mkv', 'avi', 'mov'].includes(ext)) {
      return <Film size={20} color="#a855f7" />;
    }
    if (contentType?.startsWith('audio/') || ['mp3', 'wav', 'ogg', 'flac'].includes(ext)) {
      return <Music size={20} color="#ec4899" />;
    }
    if (['zip', 'tar', 'gz', 'rar', '7z'].includes(ext)) {
      return <Archive size={20} color="#f59e0b" />;
    }
    if (['js', 'jsx', 'ts', 'tsx', 'py', 'json', 'html', 'css', 'yaml', 'yml'].includes(ext)) {
      return <Code size={20} color="#10b981" />;
    }
    if (contentType?.includes('pdf') || ['pdf', 'doc', 'docx', 'txt', 'md'].includes(ext)) {
      return <FileText size={20} color="#60a5fa" />;
    }
    return <FileIcon size={20} color="#94a3b8" />;
  };

  const totalBytesUsed = files.reduce((acc, f) => acc + (f.size_bytes || 0), 0);

  return (
    <div className="file-manager-container">
      {/* Toast Alert */}
      {toast && (
        <div className={`toast-notification ${toast.type === 'success' ? 'toast-success' : 'toast-error'}`}>
          {toast.type === 'success' ? <CheckCircle2 size={18} /> : <AlertCircle size={18} />}
          <span>{toast.text}</span>
        </div>
      )}

      {/* Preview Modal */}
      {selectedPreviewFile && (
        <FilePreviewModal 
          isOpen={Boolean(selectedPreviewFile)} 
          file={selectedPreviewFile} 
          onClose={() => setSelectedPreviewFile(null)} 
        />
      )}

      {/* Version Modal */}
      {selectedVersionFile && (
        <VersionModal 
          isOpen={Boolean(selectedVersionFile)} 
          file={selectedVersionFile} 
          onClose={() => setSelectedVersionFile(null)} 
          onFileUpdated={() => fetchFileList(pagination.page, search)}
        />
      )}

      {/* Share Modal */}
      {selectedShareFile && (
        <ShareModal 
          isOpen={Boolean(selectedShareFile)} 
          file={selectedShareFile} 
          onClose={() => setSelectedShareFile(null)} 
        />
      )}

      {/* Storage Summary Widgets */}
      <div className="stats-row">
        <div className="stat-card">
          <div className="stat-icon" style={{ background: 'rgba(56, 189, 248, 0.15)' }}>
            <HardDrive size={20} color="#38bdf8" />
          </div>
          <div>
            <div className="stat-label">Active Files</div>
            <div className="stat-value">{pagination.total}</div>
          </div>
        </div>

        <div className="stat-card">
          <div className="stat-icon" style={{ background: 'rgba(16, 185, 129, 0.15)' }}>
            <Layers size={20} color="#10b981" />
          </div>
          <div>
            <div className="stat-label">Storage Consumed</div>
            <div className="stat-value">{formatBytes(totalBytesUsed)}</div>
          </div>
        </div>

        <div className="stat-card">
          <div className="stat-icon" style={{ background: 'rgba(245, 158, 11, 0.15)' }}>
            <UploadCloud size={20} color="#f59e0b" />
          </div>
          <div>
            <div className="stat-label">Resumable Uploads</div>
            <div className="stat-value" style={{ fontSize: '1rem', color: '#10b981' }}>Chunking Active</div>
          </div>
        </div>
      </div>

      {/* Active Chunked Upload Progress Banner */}
      {uploadProgress && (
        <div className="upload-progress-banner">
          <div className="upload-progress-info">
            <div className="upload-progress-header">
              <span className="uploading-filename">
                <Loader2 size={16} className="spin" color="#38bdf8" />
                Uploading: {uploadProgress.filename}
              </span>
              <span className="uploading-chunk-stats">
                Chunk {uploadProgress.currentChunk} of {uploadProgress.totalChunks} ({uploadProgress.percent}%)
              </span>
            </div>
            <div className="upload-progress-track">
              <div 
                className="upload-progress-bar" 
                style={{ width: `${uploadProgress.percent}%` }}
              />
            </div>
          </div>
          <button 
            className="btn-cancel-upload" 
            onClick={handleCancelCurrentUpload}
            title="Cancel Upload"
          >
            <XCircle size={18} />
          </button>
        </div>
      )}

      {/* Upload Drop Zone */}
      <div 
        className={`upload-zone ${uploadProgress ? 'uploading' : ''}`}
        onDragOver={(e) => e.preventDefault()}
        onDrop={(e) => {
          e.preventDefault();
          if (e.dataTransfer.files && e.dataTransfer.files[0]) {
            handleFileUpload(e.dataTransfer.files[0]);
          }
        }}
        onClick={() => fileInputRef.current?.click()}
      >
        <input 
          ref={fileInputRef} 
          type="file" 
          style={{ display: 'none' }} 
          onChange={(e) => {
            if (e.target.files && e.target.files[0]) {
              handleFileUpload(e.target.files[0]);
            }
          }}
        />
        <div className="upload-zone-content">
          <div className="upload-icon-circle">
            <UploadCloud size={28} color="#38bdf8" />
          </div>
          <div>
            <h3 style={{ fontSize: '1.05rem', fontWeight: 700, marginBottom: '4px' }}>
              {uploadProgress ? 'Uploading chunk stream into MinIO...' : 'Click or Drag files to upload'}
            </h3>
            <p style={{ fontSize: '0.8rem', color: 'var(--text-secondary)' }}>
              Supports large chunked multipart uploads (up to 500 MB) with background thumbnail & metadata extraction.
            </p>
          </div>
        </div>
      </div>

      {/* Toolbar: Search and Refresh */}
      <div className="file-toolbar">
        <div className="search-box">
          <Search size={16} className="search-icon" />
          <input 
            type="text" 
            placeholder="Search files by name..." 
            value={search}
            onChange={handleSearchChange}
          />
        </div>

        <div style={{ display: 'flex', gap: '0.75rem', alignItems: 'center' }}>
          <button 
            onClick={() => fetchFileList(pagination.page, search)} 
            disabled={loading}
            className="btn-secondary"
            title="Refresh File List"
          >
            <RefreshCw size={15} className={loading ? 'spin' : ''} />
            <span>Refresh</span>
          </button>
        </div>
      </div>

      {/* File List Table */}
      <div className="file-table-wrapper">
        <table className="file-table">
          <thead>
            <tr>
              <th>File Name</th>
              <th style={{ width: '100px' }}>Size</th>
              <th style={{ width: '115px' }}>Status</th>
              <th style={{ width: '95px' }}>Versions</th>
              <th style={{ width: '150px' }}>Uploaded Date</th>
              <th style={{ width: '210px', textAlign: 'right' }}>Actions</th>
            </tr>
          </thead>
          <tbody>
            {files.length === 0 ? (
              <tr>
                <td colSpan="6" style={{ textAlign: 'center', padding: '3rem 1rem', color: 'var(--text-muted)' }}>
                  {loading ? 'Loading file catalog...' : (search ? 'No files match your search query.' : 'No files uploaded yet. Upload your first file above!')}
                </td>
              </tr>
            ) : (
              files.map((file) => (
                <tr key={file.id}>
                  <td>
                    <div className="file-name-cell">
                      <div className="file-icon-box">
                        {getFileIcon(file.content_type, file.original_filename)}
                      </div>
                      <span className="file-name-text" title={file.original_filename}>
                        {file.original_filename}
                      </span>
                    </div>
                  </td>
                  <td>
                    <span className="file-size-badge">{formatBytes(file.size_bytes)}</span>
                  </td>
                  <td>
                    <span className={`processing-badge badge-${file.processing_status || 'completed'}`}>
                      {file.processing_status === 'processing' && <Loader2 size={12} className="spin" />}
                      {file.processing_status === 'completed' && <CheckCircle2 size={12} />}
                      <span>{file.processing_status || 'completed'}</span>
                    </span>
                  </td>
                  <td>
                    <button 
                      onClick={() => setSelectedVersionFile(file)}
                      className="version-tag-btn"
                      title="Inspect version history"
                    >
                      <GitBranch size={12} />
                      <span>{file.version_count || 1} {file.version_count === 1 ? 'ver' : 'vers'}</span>
                    </button>
                  </td>
                  <td>
                    <div className="file-date-cell">
                      <Clock size={13} />
                      <span>{new Date(file.created_at).toLocaleDateString()} {new Date(file.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}</span>
                    </div>
                  </td>
                  <td style={{ textAlign: 'right' }}>
                    <div className="action-buttons-group">
                      <button 
                        onClick={() => setSelectedPreviewFile(file)} 
                        className="btn-action-icon btn-preview"
                        title="Preview & Metadata"
                      >
                        <Eye size={14} />
                      </button>

                      <button 
                        onClick={() => handleDownload(file)} 
                        className="btn-action-icon btn-download"
                        title="Download File"
                      >
                        <Download size={14} />
                      </button>

                      <button 
                        onClick={() => setSelectedShareFile(file)} 
                        className="btn-action-icon btn-share"
                        title="Share File Link"
                      >
                        <Share2 size={14} />
                      </button>

                      <button 
                        onClick={() => setSelectedVersionFile(file)} 
                        className="btn-action-icon btn-versions"
                        title="Manage Versions"
                      >
                        <GitBranch size={14} />
                      </button>

                      {confirmTrashId === file.id ? (
                        <div className="confirm-delete-box">
                          <button 
                            onClick={() => handleMoveToTrash(file)} 
                            className="btn-danger-small"
                          >
                            Trash
                          </button>
                          <button 
                            onClick={() => setConfirmTrashId(null)} 
                            className="btn-secondary-small"
                          >
                            Cancel
                          </button>
                        </div>
                      ) : (
                        <button 
                          onClick={() => setConfirmTrashId(file.id)} 
                          className="btn-action-icon btn-delete"
                          title="Move to Recycle Bin"
                        >
                          <Trash2 size={14} />
                        </button>
                      )}
                    </div>
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>

      {/* Pagination Controls */}
      {pagination.total_pages > 1 && (
        <div className="pagination-bar">
          <button 
            disabled={pagination.page <= 1} 
            onClick={() => fetchFileList(pagination.page - 1, search)}
            className="btn-secondary btn-pagination"
          >
            Previous
          </button>
          <span className="page-indicator">
            Page {pagination.page} of {pagination.total_pages} ({pagination.total} total files)
          </span>
          <button 
            disabled={pagination.page >= pagination.total_pages} 
            onClick={() => fetchFileList(pagination.page + 1, search)}
            className="btn-secondary btn-pagination"
          >
            Next
          </button>
        </div>
      )}
    </div>
  );
}
