import React, { useState, useEffect } from 'react';
import { 
  Trash2, 
  RotateCcw, 
  AlertTriangle, 
  Clock, 
  HardDrive, 
  RefreshCw, 
  CheckCircle2, 
  AlertCircle, 
  FileText 
} from 'lucide-react';
import { listTrash, restoreFromTrash, permanentDeleteFile, emptyTrash } from '../services/api';

export default function RecycleBin({ onRestoreSuccess }) {
  const [trashFiles, setTrashFiles] = useState([]);
  const [loading, setLoading] = useState(true);
  const [toast, setToast] = useState(null);
  const [confirmDeleteId, setConfirmDeleteId] = useState(null);
  const [confirmEmpty, setConfirmEmpty] = useState(false);
  const [actionLoading, setActionLoading] = useState(false);

  const showToast = (type, text) => {
    setToast({ type, text });
    setTimeout(() => setToast(null), 4500);
  };

  const fetchTrash = async () => {
    setLoading(true);
    const res = await listTrash();
    if (res.ok) {
      setTrashFiles(res.data.files || []);
    } else {
      showToast('error', res.error);
    }
    setLoading(false);
  };

  useEffect(() => {
    fetchTrash();
  }, []);

  const handleRestore = async (file) => {
    setActionLoading(true);
    const res = await restoreFromTrash(file.id);
    if (res.ok) {
      showToast('success', `Restored "${file.original_filename}" to your active files.`);
      setTrashFiles((prev) => prev.filter((f) => f.id !== file.id));
      if (onRestoreSuccess) onRestoreSuccess();
    } else {
      showToast('error', res.error);
    }
    setActionLoading(false);
  };

  const handlePermanentDelete = async (file) => {
    setActionLoading(true);
    const res = await permanentDeleteFile(file.id);
    if (res.ok) {
      showToast('success', `"${file.original_filename}" and its versions permanently purged.`);
      setTrashFiles((prev) => prev.filter((f) => f.id !== file.id));
      setConfirmDeleteId(null);
    } else {
      showToast('error', res.error);
    }
    setActionLoading(false);
  };

  const handleEmptyTrash = async () => {
    setActionLoading(true);
    const res = await emptyTrash();
    if (res.ok) {
      showToast('success', 'Recycle bin emptied successfully.');
      setTrashFiles([]);
      setConfirmEmpty(false);
    } else {
      showToast('error', res.error);
    }
    setActionLoading(false);
  };

  const formatBytes = (bytes) => {
    if (!bytes || bytes === 0) return '0 B';
    const k = 1024;
    const sizes = ['B', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
  };

  return (
    <div className="recycle-bin-container">
      {/* Toast Alert */}
      {toast && (
        <div className={`toast-notification ${toast.type === 'success' ? 'toast-success' : 'toast-error'}`}>
          {toast.type === 'success' ? <CheckCircle2 size={18} /> : <AlertCircle size={18} />}
          <span>{toast.text}</span>
        </div>
      )}

      {/* Header & Controls */}
      <div className="section-title">
        <div>
          <h2>
            <span>Recycle Bin</span>
            <span style={{ fontSize: '0.85rem', color: 'var(--text-muted)', fontWeight: 'normal' }}>
              ({trashFiles.length} {trashFiles.length === 1 ? 'file' : 'files'} in trash)
            </span>
          </h2>
          <p style={{ fontSize: '0.825rem', color: 'var(--text-secondary)', marginTop: '4px' }}>
            Items in the recycle bin preserve version history and can be restored or permanently removed.
          </p>
        </div>

        <div style={{ display: 'flex', gap: '0.75rem', alignItems: 'center' }}>
          <button 
            onClick={fetchTrash} 
            disabled={loading}
            className="btn-secondary"
            title="Refresh Recycle Bin"
          >
            <RefreshCw size={15} className={loading ? 'spin' : ''} />
            <span>Refresh</span>
          </button>

          {trashFiles.length > 0 && (
            confirmEmpty ? (
              <div className="confirm-delete-box">
                <button 
                  onClick={handleEmptyTrash}
                  className="btn-danger-small"
                  disabled={actionLoading}
                >
                  {actionLoading ? 'Purging...' : 'Confirm Empty Trash'}
                </button>
                <button 
                  onClick={() => setConfirmEmpty(false)}
                  className="btn-secondary-small"
                >
                  Cancel
                </button>
              </div>
            ) : (
              <button 
                onClick={() => setConfirmEmpty(true)}
                className="btn-secondary"
                style={{ borderColor: 'rgba(244, 63, 94, 0.4)', color: 'var(--accent-rose)' }}
              >
                <Trash2 size={15} />
                <span>Empty Trash</span>
              </button>
            )
          )}
        </div>
      </div>

      {/* Deleted Files Table */}
      <div className="file-table-wrapper">
        <table className="file-table">
          <thead>
            <tr>
              <th>File Name</th>
              <th>Size</th>
              <th>Deleted On</th>
              <th style={{ textAlign: 'right' }}>Actions</th>
            </tr>
          </thead>
          <tbody>
            {trashFiles.length === 0 ? (
              <tr>
                <td colSpan="4" style={{ textAlign: 'center', padding: '3.5rem 1rem', color: 'var(--text-muted)' }}>
                  <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: '0.75rem' }}>
                    <Trash2 size={36} color="var(--text-muted)" style={{ opacity: 0.5 }} />
                    <span>Your Recycle Bin is empty.</span>
                  </div>
                </td>
              </tr>
            ) : (
              trashFiles.map((file) => (
                <tr key={file.id}>
                  <td>
                    <div className="file-name-cell">
                      <div className="file-icon-box">
                        <FileText size={18} color="#94a3b8" />
                      </div>
                      <div>
                        <span className="file-name-text" title={file.original_filename}>
                          {file.original_filename}
                        </span>
                        <div style={{ fontSize: '0.72rem', color: 'var(--text-muted)' }}>
                          {file.version_count} {file.version_count === 1 ? 'version' : 'versions'} saved
                        </div>
                      </div>
                    </div>
                  </td>
                  <td>
                    <span className="file-size-badge">{formatBytes(file.size_bytes)}</span>
                  </td>
                  <td>
                    <div className="file-date-cell">
                      <Clock size={13} />
                      <span>{file.deleted_at ? new Date(file.deleted_at).toLocaleString() : 'Recently'}</span>
                    </div>
                  </td>
                  <td style={{ textAlign: 'right' }}>
                    <div className="action-buttons-group">
                      <button 
                        onClick={() => handleRestore(file)}
                        className="btn-secondary btn-action-icon"
                        title="Restore to Active Files"
                        style={{ color: '#10b981' }}
                      >
                        <RotateCcw size={15} />
                      </button>

                      {confirmDeleteId === file.id ? (
                        <div className="confirm-delete-box">
                          <button 
                            onClick={() => handlePermanentDelete(file)}
                            className="btn-danger-small"
                            disabled={actionLoading}
                          >
                            Purge
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
                          onClick={() => setConfirmDeleteId(file.id)}
                          className="btn-action-icon btn-delete"
                          title="Permanently Delete"
                        >
                          <Trash2 size={15} />
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
    </div>
  );
}
