import React, { useState, useEffect } from 'react';
import { 
  BarChart3, 
  HardDrive, 
  Files, 
  Trash2, 
  Share2, 
  History, 
  RefreshCw, 
  PieChart, 
  TrendingUp, 
  FileText, 
  Image as ImageIcon, 
  Video, 
  Music, 
  Archive, 
  Code2, 
  Folder
} from 'lucide-react';
import { getAnalyticsOverview } from '../services/api';

function formatBytes(bytes) {
  if (bytes === 0 || !bytes) return '0 B';
  const k = 1024;
  const sizes = ['B', 'KB', 'MB', 'GB', 'TB'];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
}

const CATEGORY_ICONS = {
  Documents: <FileText size={18} color="#38bdf8" />,
  Images: <ImageIcon size={18} color="#ec4899" />,
  Video: <Video size={18} color="#a855f7" />,
  Audio: <Music size={18} color="#eab308" />,
  Archives: <Archive size={18} color="#f97316" />,
  Code: <Code2 size={18} color="#10b981" />,
  Other: <Folder size={18} color="#94a3b8" />
};

const CATEGORY_COLORS = {
  Documents: '#38bdf8',
  Images: '#ec4899',
  Video: '#a855f7',
  Audio: '#eab308',
  Archives: '#f97316',
  Code: '#10b981',
  Other: '#94a3b8'
};

export default function AnalyticsDashboard() {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const fetchAnalytics = async () => {
    setLoading(true);
    setError(null);
    const res = await getAnalyticsOverview();
    if (res.ok) {
      setData(res.data);
    } else {
      setError(res.error || 'Failed to load storage analytics');
    }
    setLoading(false);
  };

  useEffect(() => {
    fetchAnalytics();
  }, []);

  if (loading) {
    return (
      <div className="file-manager-container">
        <div className="empty-state">
          <RefreshCw size={36} className="spin-icon" color="#38bdf8" />
          <p style={{ marginTop: '16px' }}>Computing storage metrics & analytics...</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="file-manager-container">
        <div className="error-banner">
          <span>{error}</span>
          <button className="btn-secondary" onClick={fetchAnalytics} style={{ marginLeft: '12px' }}>
            Retry
          </button>
        </div>
      </div>
    );
  }

  const summary = data?.summary || {};
  const distribution = data?.file_type_distribution || [];
  const timeline = data?.upload_timeline || [];

  return (
    <div className="analytics-container">
      {/* Header Controls */}
      <div className="analytics-header">
        <div>
          <h2>Storage & Usage Analytics</h2>
          <p className="analytics-subtitle">
            Real-time storage distribution, version volume, sharing metrics, and upload activity.
          </p>
        </div>
        <button className="btn-secondary" onClick={fetchAnalytics}>
          <RefreshCw size={15} />
          <span>Refresh</span>
        </button>
      </div>

      {/* Summary Stat Cards Grid */}
      <div className="analytics-grid">
        {/* Card 1: Active Files */}
        <div className="analytics-card">
          <div className="analytics-card-header">
            <span className="analytics-card-title">Active Files</span>
            <div className="analytics-icon-badge badge-blue">
              <Files size={18} color="#38bdf8" />
            </div>
          </div>
          <div className="analytics-card-value">{summary.active_files_count || 0}</div>
          <div className="analytics-card-footer">
            <span>Primary catalog files</span>
          </div>
        </div>

        {/* Card 2: Total Storage */}
        <div className="analytics-card">
          <div className="analytics-card-header">
            <span className="analytics-card-title">Storage Used</span>
            <div className="analytics-icon-badge badge-purple">
              <HardDrive size={18} color="#a855f7" />
            </div>
          </div>
          <div className="analytics-card-value">{formatBytes(summary.active_storage_bytes)}</div>
          <div className="analytics-card-footer">
            <span>All versions: {formatBytes(summary.total_all_versions_storage_bytes)}</span>
          </div>
        </div>

        {/* Card 3: Versions Total */}
        <div className="analytics-card">
          <div className="analytics-card-header">
            <span className="analytics-card-title">File Versions</span>
            <div className="analytics-icon-badge badge-green">
              <History size={18} color="#10b981" />
            </div>
          </div>
          <div className="analytics-card-value">{summary.total_versions_count || 0}</div>
          <div className="analytics-card-footer">
            <span>Historical snapshots preserved</span>
          </div>
        </div>

        {/* Card 4: Active Shares */}
        <div className="analytics-card">
          <div className="analytics-card-header">
            <span className="analytics-card-title">Active Sharing Links</span>
            <div className="analytics-icon-badge badge-yellow">
              <Share2 size={18} color="#eab308" />
            </div>
          </div>
          <div className="analytics-card-value">{summary.active_shares_count || 0}</div>
          <div className="analytics-card-footer">
            <span>Total links generated: {summary.total_shares_count || 0}</span>
          </div>
        </div>

        {/* Card 5: Recycle Bin */}
        <div className="analytics-card">
          <div className="analytics-card-header">
            <span className="analytics-card-title">Recycle Bin</span>
            <div className="analytics-icon-badge badge-red">
              <Trash2 size={18} color="#ef4444" />
            </div>
          </div>
          <div className="analytics-card-value">{summary.trash_files_count || 0}</div>
          <div className="analytics-card-footer">
            <span>Trash storage: {formatBytes(summary.trash_storage_bytes)}</span>
          </div>
        </div>
      </div>

      {/* Two Column Layout: File Type Distribution & Upload Timeline */}
      <div className="analytics-sections-row">
        {/* Category Breakdown */}
        <div className="analytics-panel">
          <div className="panel-title">
            <PieChart size={18} color="#38bdf8" />
            <span>File Type Distribution</span>
          </div>

          <div className="category-bars-list">
            {distribution.map((cat) => (
              <div key={cat.category} className="category-bar-item">
                <div className="category-bar-header">
                  <div className="category-label">
                    {CATEGORY_ICONS[cat.category] || <Folder size={18} />}
                    <span className="category-name">{cat.category}</span>
                  </div>
                  <div className="category-meta">
                    <span className="category-count">{cat.count} {cat.count === 1 ? 'file' : 'files'}</span>
                    <span className="category-size">{formatBytes(cat.size_bytes)}</span>
                    <span className="category-pct">({cat.percentage_storage}%)</span>
                  </div>
                </div>
                <div className="progress-track">
                  <div 
                    className="progress-fill" 
                    style={{ 
                      width: `${Math.max(cat.percentage_storage, cat.count > 0 ? 3 : 0)}%`,
                      backgroundColor: CATEGORY_COLORS[cat.category] || '#38bdf8'
                    }}
                  />
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Upload Timeline Activity */}
        <div className="analytics-panel">
          <div className="panel-title">
            <TrendingUp size={18} color="#10b981" />
            <span>Upload Activity Over Time</span>
          </div>

          {timeline.length === 0 ? (
            <div className="empty-state" style={{ padding: '30px 10px' }}>
              <p>No upload history recorded yet.</p>
            </div>
          ) : (
            <div className="timeline-activity-list">
              {timeline.map((t) => (
                <div key={t.date} className="timeline-activity-item">
                  <div className="timeline-date-badge">{t.date}</div>
                  <div className="timeline-stats">
                    <span className="timeline-count">{t.count} {t.count === 1 ? 'upload' : 'uploads'}</span>
                    <span className="timeline-size">{formatBytes(t.size_bytes)}</span>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
