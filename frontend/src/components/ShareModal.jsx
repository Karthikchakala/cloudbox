import React, { useState, useEffect } from 'react';
import { 
  Share2, 
  Link as LinkIcon, 
  Copy, 
  Check, 
  Lock, 
  Clock, 
  Download, 
  Trash2, 
  X, 
  AlertCircle, 
  CheckCircle2, 
  ShieldAlert 
} from 'lucide-react';
import { createShareLink, listShareLinks, revokeShareLink } from '../services/api';

export default function ShareModal({ isOpen, file, onClose }) {
  const [tab, setTab] = useState('create'); // 'create' | 'manage'
  const [permission, setPermission] = useState('download');
  const [expireOption, setExpireOption] = useState('24h');
  const [password, setPassword] = useState('');
  const [maxDownloads, setMaxDownloads] = useState('');
  const [generatedLink, setGeneratedLink] = useState(null);
  const [copied, setCopied] = useState(false);
  const [shares, setShares] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');

  const fetchShares = async () => {
    if (!file) return;
    setLoading(true);
    const res = await listShareLinks(file.id);
    if (res.ok) {
      setShares(res.data.shares || []);
    }
    setLoading(false);
  };

  useEffect(() => {
    if (isOpen && file) {
      setGeneratedLink(null);
      setError('');
      setSuccess('');
      fetchShares();
    }
  }, [isOpen, file]);

  if (!isOpen || !file) return null;

  const handleCreateShare = async (e) => {
    e.preventDefault();
    setError('');
    setLoading(true);

    let expiresAt = null;
    const now = new Date();
    if (expireOption === '1h') {
      expiresAt = new Date(now.getTime() + 60 * 60 * 1000).toISOString();
    } else if (expireOption === '24h') {
      expiresAt = new Date(now.getTime() + 24 * 60 * 60 * 1000).toISOString();
    } else if (expireOption === '7d') {
      expiresAt = new Date(now.getTime() + 7 * 24 * 60 * 60 * 1000).toISOString();
    }

    const payload = {
      permission,
      expires_at: expiresAt,
      password: password.trim() ? password : null,
      max_downloads: maxDownloads ? parseInt(maxDownloads) : null,
    };

    const res = await createShareLink(file.id, payload);
    if (res.ok) {
      const fullUrl = `${window.location.origin}${res.data.share_url}`;
      setGeneratedLink(fullUrl);
      fetchShares();
    } else {
      setError(res.error);
    }
    setLoading(false);
  };

  const handleCopy = () => {
    if (!generatedLink) return;
    navigator.clipboard.writeText(generatedLink);
    setCopied(true);
    setTimeout(() => setCopied(false), 3000);
  };

  const handleRevoke = async (shareId) => {
    setError('');
    const res = await revokeShareLink(shareId);
    if (res.ok) {
      setSuccess('Share link revoked immediately.');
      fetchShares();
    } else {
      setError(res.error);
    }
  };

  return (
    <div className="modal-overlay">
      <div className="modal-card modal-large">
        <button className="modal-close" onClick={onClose} aria-label="Close modal">
          <X size={20} />
        </button>

        <div className="modal-header-with-icon">
          <div className="modal-icon-badge" style={{ background: 'rgba(99, 102, 241, 0.15)' }}>
            <Share2 size={24} color="#818cf8" />
          </div>
          <div>
            <h2>Share File</h2>
            <p className="modal-subtitle">
              Generate secure, revocable sharing links for <strong style={{ color: '#f1f5f9' }}>{file.original_filename}</strong>
            </p>
          </div>
        </div>

        <div className="auth-tabs" style={{ marginBottom: '1.25rem' }}>
          <button 
            type="button"
            className={`auth-tab ${tab === 'create' ? 'active' : ''}`}
            onClick={() => setTab('create')}
          >
            Create Share Link
          </button>
          <button 
            type="button"
            className={`auth-tab ${tab === 'manage' ? 'active' : ''}`}
            onClick={() => setTab('manage')}
          >
            Active Links ({shares.filter(s => s.is_active).length})
          </button>
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

        {tab === 'create' ? (
          <div>
            {generatedLink ? (
              <div className="generated-link-box">
                <div className="alert-success" style={{ marginBottom: '1rem' }}>
                  <CheckCircle2 size={18} />
                  <span>Public sharing link generated! Send this URL to your recipient.</span>
                </div>
                <label style={{ fontSize: '0.8rem', color: 'var(--text-secondary)', fontWeight: 600 }}>
                  Shareable Link:
                </label>
                <div className="link-input-group">
                  <input type="text" readOnly value={generatedLink} />
                  <button onClick={handleCopy} className="btn-primary" style={{ minWidth: '100px' }}>
                    {copied ? <Check size={16} /> : <Copy size={16} />}
                    <span>{copied ? 'Copied!' : 'Copy'}</span>
                  </button>
                </div>
                <button 
                  onClick={() => { setGeneratedLink(null); setPassword(''); setMaxDownloads(''); }}
                  className="btn-secondary"
                  style={{ marginTop: '1rem', width: '100%' }}
                >
                  Create Another Link
                </button>
              </div>
            ) : (
              <form onSubmit={handleCreateShare} className="auth-form">
                <div className="form-group">
                  <label>Permission Level</label>
                  <select 
                    value={permission} 
                    onChange={(e) => setPermission(e.target.value)}
                    className="select-field"
                  >
                    <option value="download">Download & View</option>
                    <option value="view">View Only</option>
                  </select>
                </div>

                <div className="form-group">
                  <label>Link Expiration</label>
                  <select 
                    value={expireOption} 
                    onChange={(e) => setExpireOption(e.target.value)}
                    className="select-field"
                  >
                    <option value="1h">Expires in 1 Hour</option>
                    <option value="24h">Expires in 24 Hours (Default)</option>
                    <option value="7d">Expires in 7 Days</option>
                    <option value="never">Never Expires</option>
                  </select>
                </div>

                <div className="form-group">
                  <label>Password Protection (Optional)</label>
                  <div className="input-with-icon">
                    <Lock size={18} className="field-icon" />
                    <input 
                      type="password"
                      placeholder="Leave blank for open public access"
                      value={password}
                      onChange={(e) => setPassword(e.target.value)}
                    />
                  </div>
                </div>

                <div className="form-group">
                  <label>Download Limit (Optional)</label>
                  <div className="input-with-icon">
                    <Download size={18} className="field-icon" />
                    <input 
                      type="number"
                      min="1"
                      placeholder="e.g. 5 (Leave blank for unlimited)"
                      value={maxDownloads}
                      onChange={(e) => setMaxDownloads(e.target.value)}
                    />
                  </div>
                </div>

                <button 
                  type="submit" 
                  className="btn-primary" 
                  disabled={loading}
                  style={{ marginTop: '0.5rem', width: '100%' }}
                >
                  <LinkIcon size={16} />
                  <span>{loading ? 'Generating Link...' : 'Generate Sharing Link'}</span>
                </button>
              </form>
            )}
          </div>
        ) : (
          /* Manage Links Tab */
          <div className="modal-table-wrapper">
            <table className="modal-table">
              <thead>
                <tr>
                  <th>Status</th>
                  <th>Expiration</th>
                  <th>Downloads</th>
                  <th>Security</th>
                  <th style={{ textAlign: 'right' }}>Actions</th>
                </tr>
              </thead>
              <tbody>
                {shares.length === 0 ? (
                  <tr>
                    <td colSpan="5" style={{ textAlign: 'center', padding: '2rem', color: 'var(--text-muted)' }}>
                      No sharing links created yet.
                    </td>
                  </tr>
                ) : (
                  shares.map((s) => (
                    <tr key={s.id}>
                      <td>
                        <span className={`service-badge ${s.is_active ? 'badge-online' : 'badge-error'}`}>
                          {s.is_active ? 'Active' : (s.revoked_at ? 'Revoked' : 'Expired')}
                        </span>
                      </td>
                      <td>
                        <span style={{ fontSize: '0.8rem', color: 'var(--text-secondary)' }}>
                          {s.expires_at ? new Date(s.expires_at).toLocaleString() : 'Never'}
                        </span>
                      </td>
                      <td>
                        <span className="file-size-badge">
                          {s.download_count} {s.max_downloads ? `/ ${s.max_downloads}` : ''}
                        </span>
                      </td>
                      <td>
                        {s.has_password ? (
                          <span style={{ display: 'inline-flex', alignItems: 'center', gap: '4px', color: '#fbbf24', fontSize: '0.75rem' }}>
                            <Lock size={12} /> Password
                          </span>
                        ) : (
                          <span style={{ color: 'var(--text-muted)', fontSize: '0.75rem' }}>Public</span>
                        )}
                      </td>
                      <td style={{ textAlign: 'right' }}>
                        {s.is_active && (
                          <button 
                            onClick={() => handleRevoke(s.id)}
                            className="btn-danger-small"
                            title="Revoke Link Immediately"
                          >
                            Revoke
                          </button>
                        )}
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}
