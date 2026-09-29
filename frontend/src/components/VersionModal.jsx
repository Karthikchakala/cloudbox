import React, { useState, useEffect, useRef } from 'react';
import { 
  GitBranch, 
  UploadCloud, 
  Download, 
  RotateCcw, 
  Trash2, 
  X, 
  CheckCircle2, 
  AlertCircle, 
  Clock, 
  Hash, 
  FileText 
} from 'lucide-react';
import { listVersions, uploadNewVersion, downloadVersion, restoreVersion, deleteVersion } from '../services/api';

export default function VersionModal({ isOpen, file, onClose, onFileUpdated }) {
  const [versions, setVersions] = useState([]);
  const [loading, setLoading] = useState(true);
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');
  const [confirmRestoreId, setConfirmRestoreId] = useState(null);
  const [confirmDeleteId, setConfirmDeleteId] = useState(null);
  const fileInputRef = useRef(null);

  const fetchVersions = async () => {
    if (!file) return;
    setLoading(true);
    setError('');
    const res = await listVersions(file.id);
    if (res.ok) {
      setVersions(res.data.versions || []);
    } else {
      setError(res.error);
    }
    setLoading(false);
  };

  useEffect(() => {
    if (isOpen && file) {
      fetchVersions();
    }
  }, [isOpen, file]);

  if (!isOpen || !file) return null;

  const showSuccess = (msg) => {
    setSuccess(msg);
    setTimeout(() => setSuccess(''), 4000);
  };

  const handleUploadVersion = async (fileObj) => {
    if (!fileObj) return;
    setUploading(true);
    setError('');
    const res = await uploadNewVersion(file.id, fileObj);
    if (res.ok) {
      showSuccess(`Version ${res.data.version.version_number} uploaded successfully!`);
      fetchVersions();
      if (onFileUpdated) onFileUpdated();
    } else {
      setError(res.error);
    }
    setUploading(false);
    if (fileInputRef.current) fileInputRef.current.value = '';
  };

  const handleRestore = async (version) => {
    setError('');
    const res = await restoreVersion(file.id, version.id);
    if (res.ok) {
      showSuccess(`Restored Version ${version.version_number} as latest version.`);
      setConfirmRestoreId(null);
      fetchVersions();
      if (onFileUpdated) onFileUpdated();
    } else {
      setError(res.error);
    }
  };

  const handleDeleteVersion = async (version) => {
    setError('');
    const res = await deleteVersion(file.id, version.id);
    if (res.ok) {
      showSuccess(`Version ${version.version_number} deleted.`);
      setConfirmDeleteId(null);
      fetchVersions();
      if (onFileUpdated) onFileUpdated();
    } else {
      setError(res.error);
    }
  };

  const formatBytes = (bytes) => {
    if (!bytes || bytes === 0) return '0 B';
    const k = 1024;
    const sizes = ['B', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
  };

  return (
    <div className="modal-overlay">
      <div className="modal-card modal-large">
        <button className="modal-close" onClick={onClose} aria-label="Close modal">
          <X size={20} />
        </button>

        <div className="modal-header-with-icon">
          <div className="modal-icon-badge" style={{ background: 'rgba(56, 189, 248, 0.15)' }}>
            <GitBranch size={24} color="#38bdf8" />
          </div>
          <div>
            <h2>Version History</h2>
            <p className="modal-subtitle">
              Manage revisions for <strong style={{ color: '#f1f5f9' }}>{file.original_filename}</strong>
            </p>
          </div>
        </div>

        {error && (
          <div className="alert-error">
            <AlertCircle size={18} />
            <span>{error}</span>
          </div>
        )}

        {success && (
          <div className="alert-success">
            <CheckCircle2 size={18} />
            <span>{success}</span>
          </div>
        )}

        {/* Upload New Version Button */}
        <div className="version-upload-bar">
          <div>
            <span style={{ fontSize: '0.85rem', fontWeight: 600, color: 'var(--text-secondary)' }}>
              Create New Revision:
            </span>
          </div>
          <input 
            ref={fileInputRef} 
            type="file" 
            style={{ display: 'none' }}
            onChange={(e) => {
              if (e.target.files && e.target.files[0]) {
                handleUploadVersion(e.target.files[0]);
              }
            }}
          />
          <button 
            onClick={() => fileInputRef.current?.click()} 
            disabled={uploading}
            className="btn-primary"
            style={{ padding: '0.45rem 1rem', fontSize: '0.85rem' }}
          >
            <UploadCloud size={16} />
            <span>{uploading ? 'Uploading Version...' : 'Upload New Version'}</span>
          </button>
        </div>

        {/* Versions Table */}
        <div className="modal-table-wrapper">
          <table className="modal-table">
            <thead>
              <tr>
                <th>Version</th>
                <th>File Size</th>
                <th>Created At</th>
                <th>Checksum</th>
                <th style={{ textAlign: 'right' }}>Actions</th>
              </tr>
            </thead>
            <tbody>
              {loading ? (
                <tr>
                  <td colSpan="5" style={{ textAlign: 'center', padding: '2rem', color: 'var(--text-muted)' }}>
                    Loading version history...
                  </td>
                </tr>
              ) : versions.length === 0 ? (
                <tr>
                  <td colSpan="5" style={{ textAlign: 'center', padding: '2rem', color: 'var(--text-muted)' }}>
                    No version history found.
                  </td>
                </tr>
              ) : (
                versions.map((ver) => (
                  <tr key={ver.id} className={ver.is_current ? 'row-current-version' : ''}>
                    <td>
                      <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                        <span className="version-pill">v{ver.version_number}</span>
                        {ver.is_current && <span className="current-badge">Current Active</span>}
                      </div>
                    </td>
                    <td>
                      <span className="file-size-badge">{formatBytes(ver.size_bytes)}</span>
                    </td>
                    <td>
                      <div className="file-date-cell">
                        <Clock size={12} />
                        <span>{new Date(ver.created_at).toLocaleString()}</span>
                      </div>
                    </td>
                    <td>
                      <span className="checksum-tag" title={ver.checksum_sha256}>
                        <Hash size={11} />
                        {ver.checksum_sha256.substring(0, 8)}...
                      </span>
                    </td>
                    <td style={{ textAlign: 'right' }}>
                      <div className="action-buttons-group">
                        <button 
                          onClick={() => downloadVersion(file.id, ver.id, ver.original_filename)}
                          className="btn-action-icon btn-download"
                          title="Download this version"
                        >
                          <Download size={14} />
                        </button>

                        {!ver.is_current && (
                          confirmRestoreId === ver.id ? (
                            <div className="confirm-delete-box">
                              <button 
                                onClick={() => handleRestore(ver)}
                                className="btn-primary-small"
                              >
                                Confirm
                              </button>
                              <button 
                                onClick={() => setConfirmRestoreId(null)}
                                className="btn-secondary-small"
                              >
                                Cancel
                              </button>
                            </div>
                          ) : (
                            <button 
                              onClick={() => setConfirmRestoreId(ver.id)}
                              className="btn-action-icon btn-restore"
                              title="Restore this version as current"
                            >
                              <RotateCcw size={14} />
                            </button>
                          )
                        )}

                        {versions.length > 1 && (
                          confirmDeleteId === ver.id ? (
                            <div className="confirm-delete-box">
                              <button 
                                onClick={() => handleDeleteVersion(ver)}
                                className="btn-danger-small"
                              >
                                Confirm
                              </button>
                              <button 
                                onClick={() => setConfirmDeleteId(null)}
                                className="btn-secondary-small"
                              >
                                Cancel
                              </button>
                            </div>
                          ) : (
                            <button 
                              onClick={() => setConfirmDeleteId(ver.id)}
                              className="btn-action-icon btn-delete"
                              title="Delete this version"
                            >
                              <Trash2 size={14} />
                            </button>
                          )
                        )}
                      </div>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
