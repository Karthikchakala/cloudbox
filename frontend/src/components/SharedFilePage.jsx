import React, { useState, useEffect } from 'react';
import { 
  Cloud, 
  Download, 
  Lock, 
  CheckCircle2, 
  AlertCircle, 
  FileText, 
  HardDrive, 
  Clock, 
  ShieldCheck, 
  ArrowLeft 
} from 'lucide-react';
import { getSharedFileInfo, downloadSharedFile, verifySharedPassword } from '../services/api';

export default function SharedFilePage({ token, onBackHome }) {
  const [fileInfo, setFileInfo] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [password, setPassword] = useState('');
  const [isVerifying, setIsVerifying] = useState(false);
  const [passwordVerified, setPasswordVerified] = useState(false);
  const [downloading, setDownloading] = useState(false);

  const fetchInfo = async (suppliedPass = null) => {
    setLoading(true);
    setError('');
    const res = await getSharedFileInfo(token, suppliedPass);
    if (res.ok) {
      setFileInfo(res.data);
      if (!res.data.requires_password) {
        setPasswordVerified(true);
      }
    } else {
      if (res.status === 410) {
        setError('This sharing link has expired, been revoked, or reached its maximum download limit.');
      } else {
        setError(res.error || 'Unable to access shared file.');
      }
    }
    setLoading(false);
  };

  useEffect(() => {
    if (token) {
      fetchInfo();
    }
  }, [token]);

  const handlePasswordSubmit = async (e) => {
    e.preventDefault();
    setError('');
    setIsVerifying(true);
    const res = await verifySharedPassword(token, password);
    if (res.ok) {
      setPasswordVerified(true);
      fetchInfo(password);
    } else {
      setError(res.error || 'Incorrect password.');
    }
    setIsVerifying(false);
  };

  const handleDownload = async () => {
    setDownloading(true);
    const passToSend = passwordVerified && password ? password : null;
    const filename = fileInfo ? fileInfo.original_filename : 'shared_file';
    const res = await downloadSharedFile(token, passToSend, filename);
    if (!res.ok) {
      setError(res.error || 'Failed to download file.');
    }
    setDownloading(false);
  };

  const formatBytes = (bytes) => {
    if (!bytes || bytes === 0) return '0 B';
    const k = 1024;
    const sizes = ['B', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
  };

  return (
    <div className="shared-page-container">
      <div className="shared-card">
        <div className="brand" style={{ justifyContent: 'center', marginBottom: '1.5rem' }}>
          <div className="brand-icon">
            <Cloud size={24} />
          </div>
          <div>
            <span className="brand-title">CloudBox Share</span>
          </div>
        </div>

        {loading ? (
          <div style={{ textAlign: 'center', padding: '3rem 0', color: 'var(--text-muted)' }}>
            Loading shared file details...
          </div>
        ) : error ? (
          <div className="shared-error-box">
            <AlertCircle size={36} color="#f43f5e" />
            <h3 style={{ fontSize: '1.2rem', fontWeight: 700, marginTop: '0.75rem', marginBottom: '0.5rem' }}>
              Link Unavailable
            </h3>
            <p style={{ fontSize: '0.9rem', color: 'var(--text-secondary)', lineHeight: 1.5, marginBottom: '1.5rem' }}>
              {error}
            </p>
            {onBackHome && (
              <button onClick={onBackHome} className="btn-secondary">
                <ArrowLeft size={16} />
                <span>Return to Home</span>
              </button>
            )}
          </div>
        ) : fileInfo && fileInfo.requires_password && !passwordVerified ? (
          /* Password Form */
          <div>
            <div className="auth-header">
              <div className="auth-icon-box" style={{ background: 'rgba(251, 191, 36, 0.15)' }}>
                <Lock size={26} color="#fbbf24" />
              </div>
              <h2>Password Protected File</h2>
              <p>This shared document requires a password to view or download.</p>
            </div>

            <form onSubmit={handlePasswordSubmit} className="auth-form">
              <div className="form-group">
                <label>Enter Password</label>
                <div className="input-with-icon">
                  <Lock size={18} className="field-icon" />
                  <input 
                    type="password"
                    placeholder="Enter security password"
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    required
                  />
                </div>
              </div>

              <button type="submit" className="btn-primary" disabled={isVerifying} style={{ width: '100%' }}>
                <span>{isVerifying ? 'Verifying...' : 'Unlock File'}</span>
              </button>
            </form>
          </div>
        ) : fileInfo ? (
          /* File Download Card */
          <div>
            <div className="shared-file-hero">
              <div className="file-icon-box" style={{ width: '56px', height: '56px', margin: '0 auto 1rem', background: 'rgba(56, 189, 248, 0.15)' }}>
                <FileText size={30} color="#38bdf8" />
              </div>
              <h2 style={{ fontSize: '1.35rem', fontWeight: 800, marginBottom: '0.35rem', wordBreak: 'break-word' }}>
                {fileInfo.original_filename}
              </h2>
              <span className="file-size-badge" style={{ fontSize: '0.85rem' }}>
                {formatBytes(fileInfo.size_bytes)}
              </span>
            </div>

            <div className="service-meta" style={{ margin: '1.5rem 0' }}>
              <div className="meta-row">
                <span>Security:</span>
                <span className="meta-val" style={{ color: '#10b981' }}>End-to-End Verified</span>
              </div>
              <div className="meta-row">
                <span>Storage Cluster:</span>
                <span className="meta-val">MinIO Object Storage</span>
              </div>
            </div>

            <button 
              onClick={handleDownload} 
              disabled={downloading} 
              className="btn-primary"
              style={{ width: '100%', padding: '0.85rem', fontSize: '1rem' }}
            >
              <Download size={18} />
              <span>{downloading ? 'Downloading...' : 'Download File'}</span>
            </button>

            {onBackHome && (
              <div style={{ textAlign: 'center', marginTop: '1.25rem' }}>
                <button onClick={onBackHome} className="btn-secondary" style={{ fontSize: '0.8rem', padding: '0.4rem 0.85rem' }}>
                  <ArrowLeft size={14} />
                  <span>Go to CloudBox Home</span>
                </button>
              </div>
            )}
          </div>
        ) : null}
      </div>
    </div>
  );
}
