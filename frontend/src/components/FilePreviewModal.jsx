import React, { useState, useEffect, useRef } from 'react';
import {
  X,
  Download,
  Eye,
  Image as ImageIcon,
  FileText,
  CheckCircle2,
  Clock,
  AlertTriangle,
  ShieldCheck,
  HardDrive,
  ZoomIn,
  ZoomOut,
  RotateCw,
  Maximize2,
  Minimize2,
  Info,
  Copy,
  Check,
  Printer,
  FileCode,
  FileSpreadsheet,
  FileArchive,
  Music,
  Video,
  ExternalLink,
  ChevronLeft
} from 'lucide-react';
import { fetchFilePreviewBlob, getFileProcessingStatus, downloadFile } from '../services/api';

function formatBytes(bytes) {
  if (bytes === 0 || !bytes) return '0 B';
  const k = 1024;
  const sizes = ['B', 'KB', 'MB', 'GB', 'TB'];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
}

function formatDate(isoStr) {
  if (!isoStr) return '—';
  try {
    const d = new Date(isoStr);
    return d.toLocaleDateString(undefined, {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    });
  } catch {
    return isoStr;
  }
}

function getFileCategory(filename, contentType) {
  const ext = (filename || '').split('.').pop().toLowerCase();
  if (/\.(jpe?g|png|gif|webp|bmp|svg|ico)$/i.test(filename) || contentType?.startsWith('image/')) return 'image';
  if (/\.pdf$/i.test(filename) || contentType?.includes('pdf')) return 'pdf';
  if (/\.(txt|md|csv|json|js|jsx|ts|tsx|py|html|css|yaml|yml|xml|sql|sh|log|env|ini|conf)$/i.test(filename) || contentType?.startsWith('text/')) return 'text';
  if (/\.(mp3|wav|ogg|m4a|aac|flac)$/i.test(filename) || contentType?.startsWith('audio/')) return 'audio';
  if (/\.(mp4|webm|mkv|mov|avi)$/i.test(filename) || contentType?.startsWith('video/')) return 'video';
  if (/\.(zip|tar|gz|7z|rar|bz2)$/i.test(filename)) return 'archive';
  return 'binary';
}

export default function FilePreviewModal({ isOpen, onClose, file }) {
  const [previewData, setPreviewData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [processingStatus, setProcessingStatus] = useState(null);
  const [showDetails, setShowDetails] = useState(false);
  
  // Viewer controls
  const [zoom, setZoom] = useState(100);
  const [rotation, setRotation] = useState(0);
  const [wordWrap, setWordWrap] = useState(true);
  const [copied, setCopied] = useState(false);
  const [checksumCopied, setChecksumCopied] = useState(false);

  useEffect(() => {
    if (!isOpen || !file) {
      setPreviewData(null);
      setProcessingStatus(null);
      setZoom(100);
      setRotation(0);
      return;
    }

    let isMounted = true;
    setLoading(true);
    setError(null);

    async function loadPreview() {
      // 1. Fetch processing status & metadata
      try {
        const statusRes = await getFileProcessingStatus(file.id);
        if (isMounted && statusRes.ok) {
          setProcessingStatus(statusRes.data);
        }
      } catch (e) {
        console.warn('Metadata fetch notice:', e);
      }

      // 2. Fetch preview blob
      try {
        const prevRes = await fetchFilePreviewBlob(file.id);
        if (isMounted) {
          if (prevRes.ok) {
            setPreviewData(prevRes);
          } else {
            setError(prevRes.error || 'Preview could not be loaded');
          }
        }
      } catch (err) {
        if (isMounted) setError(err.message || 'Error loading preview');
      }

      if (isMounted) setLoading(false);
    }

    loadPreview();

    // Keyboard navigation: Escape to close, + / - to zoom
    const handleKeyDown = (e) => {
      if (e.key === 'Escape') onClose();
      if ((e.ctrlKey || e.metaKey) && (e.key === '=' || e.key === '+')) {
        e.preventDefault();
        setZoom((z) => Math.min(300, z + 25));
      }
      if ((e.ctrlKey || e.metaKey) && e.key === '-') {
        e.preventDefault();
        setZoom((z) => Math.max(25, z - 25));
      }
      if ((e.ctrlKey || e.metaKey) && e.key === '0') {
        e.preventDefault();
        setZoom(100);
        setRotation(0);
      }
    };

    window.addEventListener('keydown', handleKeyDown);

    return () => {
      isMounted = false;
      window.removeEventListener('keydown', handleKeyDown);
      if (previewData?.blobUrl) {
        URL.revokeObjectURL(previewData.blobUrl);
      }
    };
  }, [isOpen, file]);

  if (!isOpen || !file) return null;

  const category = getFileCategory(file.original_filename, file.content_type);
  const meta = processingStatus?.extracted_metadata || file.extracted_metadata || {};

  const handleCopyText = () => {
    if (previewData?.textContent) {
      navigator.clipboard.writeText(previewData.textContent);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    }
  };

  const handleCopyChecksum = () => {
    if (file.checksum_sha256) {
      navigator.clipboard.writeText(file.checksum_sha256);
      setChecksumCopied(true);
      setTimeout(() => setChecksumCopied(false), 2000);
    }
  };

  const handlePrint = () => {
    if (category === 'text' && previewData?.textContent) {
      const printWin = window.open('', '', 'width=800,height=600');
      printWin.document.write(`<pre style="font-family: monospace; white-space: pre-wrap;">${previewData.textContent}</pre>`);
      printWin.document.close();
      printWin.focus();
      printWin.print();
      printWin.close();
    } else if (previewData?.blobUrl) {
      window.open(previewData.blobUrl, '_blank');
    }
  };

  return (
    <div className="gdrive-viewer-overlay" role="dialog" aria-modal="true">
      {/* 1. Google Drive Top Navigation Toolbar */}
      <header className="gdrive-topbar">
        {/* Left: Back/Close & File Title */}
        <div className="gdrive-topbar-left">
          <button 
            className="gdrive-icon-btn gdrive-close-btn" 
            onClick={onClose}
            title="Close viewer (Esc)"
            aria-label="Close"
          >
            <ChevronLeft size={22} />
          </button>
          
          <div className="gdrive-file-badge">
            {category === 'image' && <ImageIcon size={20} color="#38bdf8" />}
            {category === 'pdf' && <FileText size={20} color="#f43f5e" />}
            {category === 'text' && <FileCode size={20} color="#10b981" />}
            {category === 'audio' && <Music size={20} color="#a855f7" />}
            {category === 'video' && <Video size={20} color="#f59e0b" />}
            {category === 'archive' && <FileArchive size={20} color="#eab308" />}
            {category === 'binary' && <HardDrive size={20} color="#94a3b8" />}
          </div>

          <div className="gdrive-file-info-header">
            <h2 className="gdrive-file-title" title={file.original_filename}>
              {file.original_filename}
            </h2>
            <div className="gdrive-file-subtext">
              <span>{formatBytes(file.size_bytes)}</span>
              <span className="gdrive-dot">&bull;</span>
              <span>{file.content_type || 'Unknown Type'}</span>
              {file.created_at && (
                <>
                  <span className="gdrive-dot">&bull;</span>
                  <span>{formatDate(file.created_at)}</span>
                </>
              )}
            </div>
          </div>
        </div>

        {/* Center: Interactive Viewer Controls (Zoom / Rotate / Wrap) */}
        <div className="gdrive-topbar-center">
          {category === 'image' && (
            <div className="gdrive-toolbar-group">
              <button 
                className="gdrive-toolbar-btn" 
                onClick={() => setZoom((z) => Math.max(25, z - 25))} 
                title="Zoom Out (Ctrl -)"
              >
                <ZoomOut size={17} />
              </button>
              <span className="gdrive-zoom-label" onClick={() => { setZoom(100); setRotation(0); }} title="Reset Zoom">
                {zoom}%
              </span>
              <button 
                className="gdrive-toolbar-btn" 
                onClick={() => setZoom((z) => Math.min(300, z + 25))} 
                title="Zoom In (Ctrl +)"
              >
                <ZoomIn size={17} />
              </button>
              <div className="gdrive-divider" />
              <button 
                className="gdrive-toolbar-btn" 
                onClick={() => setRotation((r) => (r + 90) % 360)} 
                title="Rotate 90°"
              >
                <RotateCw size={17} />
              </button>
            </div>
          )}

          {category === 'text' && (
            <div className="gdrive-toolbar-group">
              <button 
                className={`gdrive-toolbar-btn ${wordWrap ? 'active' : ''}`}
                onClick={() => setWordWrap(!wordWrap)} 
                title={wordWrap ? 'Disable Word Wrap' : 'Enable Word Wrap'}
              >
                <span style={{ fontSize: '0.75rem', fontWeight: 600 }}>WRAP</span>
              </button>
              <div className="gdrive-divider" />
              <button 
                className="gdrive-toolbar-btn" 
                onClick={handleCopyText} 
                title="Copy contents"
              >
                {copied ? <Check size={16} color="#10b981" /> : <Copy size={16} />}
              </button>
            </div>
          )}
        </div>

        {/* Right: Actions (Print, Info, Download, Close) */}
        <div className="gdrive-topbar-right">
          {(category === 'text' || category === 'pdf' || category === 'image') && (
            <button 
              className="gdrive-icon-btn" 
              onClick={handlePrint} 
              title="Print or Open Full"
            >
              <Printer size={18} />
            </button>
          )}

          <button 
            className={`gdrive-icon-btn ${showDetails ? 'active' : ''}`}
            onClick={() => setShowDetails(!showDetails)} 
            title="Toggle File Details (i)"
          >
            <Info size={19} />
          </button>

          <button 
            className="gdrive-action-download-btn" 
            onClick={() => downloadFile(file.id, file.original_filename)}
            title="Download file to computer"
          >
            <Download size={16} />
            <span>Download</span>
          </button>

          <button 
            className="gdrive-icon-btn gdrive-exit-btn" 
            onClick={onClose}
            title="Close viewer"
          >
            <X size={20} />
          </button>
        </div>
      </header>

      {/* 2. Main Viewer Stage & Side Details Drawer */}
      <div className="gdrive-viewer-body">
        {/* Main Canvas Stage */}
        <main className="gdrive-stage">
          {loading ? (
            <div className="gdrive-loader-box">
              <div className="gdrive-spinner" />
              <p>Opening file in Drive Viewer...</p>
            </div>
          ) : error ? (
            <div className="gdrive-error-card">
              <AlertTriangle size={42} color="#f59e0b" />
              <h3>Unable to generate preview</h3>
              <p>{error}</p>
              <button 
                className="btn-primary" 
                style={{ marginTop: '16px' }}
                onClick={() => downloadFile(file.id, file.original_filename)}
              >
                <Download size={16} />
                <span>Download File ({formatBytes(file.size_bytes)})</span>
              </button>
            </div>
          ) : category === 'image' && previewData?.blobUrl ? (
            <div className="gdrive-image-viewport">
              <img
                src={previewData.blobUrl}
                alt={file.original_filename}
                className="gdrive-preview-image"
                style={{
                  transform: `scale(${zoom / 100}) rotate(${rotation}deg)`,
                  transition: 'transform 0.15s ease-out',
                }}
              />
            </div>
          ) : category === 'pdf' && previewData?.blobUrl ? (
            <div className="gdrive-pdf-container">
              <iframe
                src={previewData.blobUrl}
                title={file.original_filename}
                className="gdrive-pdf-frame"
              />
            </div>
          ) : category === 'text' && previewData?.textContent !== null ? (
            <div className="gdrive-code-container">
              <div className="gdrive-code-header">
                <span>{file.original_filename}</span>
                <span>{previewData.textContent.split('\n').length} lines &bull; {previewData.textContent.length} characters</span>
              </div>
              <div className="gdrive-code-viewport">
                <div className="gdrive-line-numbers">
                  {previewData.textContent.split('\n').map((_, idx) => (
                    <div key={idx} className="gdrive-line-num">{idx + 1}</div>
                  ))}
                </div>
                <pre className={`gdrive-code-content ${wordWrap ? 'wrap' : 'nowrap'}`}>
                  <code>{previewData.textContent}</code>
                </pre>
              </div>
            </div>
          ) : category === 'audio' && previewData?.blobUrl ? (
            <div className="gdrive-media-card">
              <div className="gdrive-media-icon">
                <Music size={56} color="#a855f7" />
              </div>
              <h3>{file.original_filename}</h3>
              <audio controls autoPlay className="gdrive-audio-player">
                <source src={previewData.blobUrl} type={file.content_type} />
                Your browser does not support audio playback.
              </audio>
            </div>
          ) : category === 'video' && previewData?.blobUrl ? (
            <div className="gdrive-video-container">
              <video controls autoPlay className="gdrive-video-player">
                <source src={previewData.blobUrl} type={file.content_type} />
                Your browser does not support video playback.
              </video>
            </div>
          ) : (
            <div className="gdrive-unsupported-card">
              <div className="gdrive-unsupported-icon">
                <FileText size={64} color="#64748b" />
              </div>
              <h3>No Preview Available</h3>
              <p>
                This file type (<code>{file.content_type || 'binary'}</code>) cannot be previewed directly in the browser.
              </p>
              <button 
                className="gdrive-action-download-btn" 
                style={{ marginTop: '20px', padding: '0.75rem 1.5rem', fontSize: '0.95rem' }}
                onClick={() => downloadFile(file.id, file.original_filename)}
              >
                <Download size={18} />
                <span>Download ({formatBytes(file.size_bytes)})</span>
              </button>
            </div>
          )}
        </main>

        {/* 3. Google Drive Collapsible Details Sidebar (Info Panel) */}
        {showDetails && (
          <aside className="gdrive-details-sidebar">
            <div className="gdrive-sidebar-header">
              <h3>File Details</h3>
              <button 
                className="gdrive-icon-btn" 
                onClick={() => setShowDetails(false)}
                title="Close details"
              >
                <X size={18} />
              </button>
            </div>

            <div className="gdrive-sidebar-content">
              {/* File Identity Card */}
              <div className="gdrive-sidebar-card">
                <div className="gdrive-sidebar-file-row">
                  <div className="gdrive-file-badge small">
                    {category === 'image' && <ImageIcon size={18} color="#38bdf8" />}
                    {category === 'pdf' && <FileText size={18} color="#f43f5e" />}
                    {category === 'text' && <FileCode size={18} color="#10b981" />}
                    {category === 'binary' && <HardDrive size={18} color="#94a3b8" />}
                  </div>
                  <div>
                    <h4 className="gdrive-sidebar-filename">{file.original_filename}</h4>
                    <span className="gdrive-sidebar-filesize">{formatBytes(file.size_bytes)}</span>
                  </div>
                </div>
              </div>

              {/* General Properties */}
              <div className="gdrive-prop-group">
                <h4 className="gdrive-prop-group-title">General Properties</h4>
                
                <div className="gdrive-prop-row">
                  <span className="gdrive-prop-label">Type</span>
                  <span className="gdrive-prop-value">{file.content_type || 'Unknown'}</span>
                </div>

                <div className="gdrive-prop-row">
                  <span className="gdrive-prop-label">Size</span>
                  <span className="gdrive-prop-value">{formatBytes(file.size_bytes)} ({file.size_bytes.toLocaleString()} bytes)</span>
                </div>

                <div className="gdrive-prop-row">
                  <span className="gdrive-prop-label">Storage Location</span>
                  <span className="gdrive-prop-value">MinIO S3 &bull; cloudbox-uploads</span>
                </div>

                <div className="gdrive-prop-row">
                  <span className="gdrive-prop-label">Created</span>
                  <span className="gdrive-prop-value">{formatDate(file.created_at)}</span>
                </div>

                {file.updated_at && (
                  <div className="gdrive-prop-row">
                    <span className="gdrive-prop-label">Modified</span>
                    <span className="gdrive-prop-value">{formatDate(file.updated_at)}</span>
                  </div>
                )}
              </div>

              {/* Extracted Metadata (if available) */}
              {(meta.width || meta.page_count !== undefined || meta.format) && (
                <div className="gdrive-prop-group">
                  <h4 className="gdrive-prop-group-title">Extracted Media Metadata</h4>
                  
                  {meta.width && (
                    <div className="gdrive-prop-row">
                      <span className="gdrive-prop-label">Dimensions</span>
                      <span className="gdrive-prop-value">{meta.width} &times; {meta.height} px</span>
                    </div>
                  )}

                  {meta.format && (
                    <div className="gdrive-prop-row">
                      <span className="gdrive-prop-label">Format</span>
                      <span className="gdrive-prop-value">{meta.format.toUpperCase()}</span>
                    </div>
                  )}

                  {meta.page_count !== undefined && (
                    <div className="gdrive-prop-row">
                      <span className="gdrive-prop-label">Pages</span>
                      <span className="gdrive-prop-value">{meta.page_count} {meta.page_count === 1 ? 'page' : 'pages'}</span>
                    </div>
                  )}
                </div>
              )}

              {/* Integrity & Security */}
              <div className="gdrive-prop-group">
                <h4 className="gdrive-prop-group-title">Integrity & Security</h4>
                
                <div className="gdrive-prop-row">
                  <span className="gdrive-prop-label">Processing</span>
                  <span className="gdrive-prop-value status-badge">
                    <CheckCircle2 size={13} color="#10b981" />
                    {processingStatus?.status || file.processing_status || 'completed'}
                  </span>
                </div>

                <div className="gdrive-prop-col">
                  <div className="gdrive-checksum-header">
                    <span className="gdrive-prop-label">SHA-256 Checksum</span>
                    <button 
                      className="gdrive-copy-mini-btn" 
                      onClick={handleCopyChecksum}
                      title="Copy SHA-256 hash"
                    >
                      {checksumCopied ? <Check size={12} color="#10b981" /> : <Copy size={12} />}
                      <span>{checksumCopied ? 'Copied' : 'Copy'}</span>
                    </button>
                  </div>
                  <code className="gdrive-checksum-code">{file.checksum_sha256}</code>
                </div>
              </div>
            </div>
          </aside>
        )}
      </div>
    </div>
  );
}
