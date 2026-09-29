import React, { useState, useEffect } from 'react';
import { getBackendHealth, getCurrentUser, setAuthToken } from '../services/api';
import ServiceStatus from '../components/ServiceStatus';
import ArchitectureOverview from '../components/ArchitectureOverview';
import FileManager from '../components/FileManager';
import RecycleBin from '../components/RecycleBin';
import SharedFilePage from '../components/SharedFilePage';
import AnalyticsDashboard from '../components/AnalyticsDashboard';
import AuthModal from '../components/AuthModal';
import { Shield, Lock, UploadCloud, CheckCircle2, Files, Trash2, BarChart3 } from 'lucide-react';

export default function Dashboard({ user, setUser, isAuthOpen, setIsAuthOpen }) {
  const [backendData, setBackendData] = useState(null);
  const [isChecking, setIsChecking] = useState(true);
  const [activeTab, setActiveTab] = useState('files'); // 'files' | 'trash' | 'analytics'
  const [sharedToken, setSharedToken] = useState(null);

  // Check if current URL path is a shared file link: /shared/:token
  useEffect(() => {
    const path = window.location.pathname;
    if (path.startsWith('/shared/')) {
      const token = path.replace('/shared/', '').trim();
      if (token) {
        setSharedToken(token);
      }
    }
  }, []);

  const checkHealth = async () => {
    setIsChecking(true);
    const result = await getBackendHealth();
    if (result.ok) {
      setBackendData(result.data);
    } else {
      setBackendData(null);
    }
    setIsChecking(false);
  };

  useEffect(() => {
    checkHealth();
    const interval = setInterval(checkHealth, 10000);
    return () => clearInterval(interval);
  }, []);

  // If public recipient viewing shared link
  if (sharedToken) {
    return (
      <SharedFilePage 
        token={sharedToken} 
        onBackHome={() => {
          window.history.pushState({}, '', '/');
          setSharedToken(null);
        }}
      />
    );
  }

  return (
    <main className="main-content">
      <AuthModal 
        isOpen={isAuthOpen} 
        onClose={() => setIsAuthOpen(false)} 
        onAuthSuccess={(loggedInUser) => {
          setUser(loggedInUser);
        }}
      />

      <section className="hero">
        <div className="hero-pill">
          <span className="hero-pill-dot"></span>
          <span>Enterprise Cloud Storage &bull; End-to-End Encryption &bull; High Availability</span>
        </div>
        <h1>Self-Hosted Cloud Storage Architecture</h1>
        <p>
          Secure and scalable cloud storage platform: reverse proxy, automated backups, 
          immutable versions, secure share links, soft-delete recycle bin, and real-time storage analytics.
        </p>
      </section>

      {/* Main Feature Area */}
      {user ? (
        <section className="dashboard-section">
          {/* Main Navigation Tabs */}
          <div className="main-nav-tabs">
            <button 
              className={`main-nav-tab ${activeTab === 'files' ? 'active' : ''}`}
              onClick={() => setActiveTab('files')}
            >
              <Files size={17} />
              <span>My Files</span>
            </button>
            <button 
              className={`main-nav-tab ${activeTab === 'trash' ? 'active' : ''}`}
              onClick={() => setActiveTab('trash')}
            >
              <Trash2 size={17} />
              <span>Recycle Bin</span>
            </button>
            <button 
              className={`main-nav-tab ${activeTab === 'analytics' ? 'active' : ''}`}
              onClick={() => setActiveTab('analytics')}
            >
              <BarChart3 size={17} />
              <span>Storage Analytics</span>
            </button>
          </div>

          {activeTab === 'files' && (
            <FileManager user={user} onOpenTrash={() => setActiveTab('trash')} />
          )}
          {activeTab === 'trash' && (
            <RecycleBin onRestoreSuccess={() => {}} />
          )}
          {activeTab === 'analytics' && (
            <AnalyticsDashboard />
          )}
        </section>
      ) : (
        <section className="unauth-banner-card">
          <div className="unauth-banner-content">
            <div className="unauth-icon-circle">
              <Lock size={32} color="#38bdf8" />
            </div>
            <h2>Sign in to Access Your Files</h2>
            <p>
              Create your account or log in to manage your files, maintain version history, 
              generate password-protected shareable links, and recover items from your recycle bin.
            </p>
            <div className="unauth-features">
              <div className="unauth-feature-item">
                <CheckCircle2 size={16} color="#10b981" />
                <span>Multi-version History</span>
              </div>
              <div className="unauth-feature-item">
                <CheckCircle2 size={16} color="#10b981" />
                <span>Secure Revocable Links</span>
              </div>
              <div className="unauth-feature-item">
                <CheckCircle2 size={16} color="#10b981" />
                <span>Safe Soft-Delete Recycle Bin</span>
              </div>
            </div>
            <button 
              onClick={() => setIsAuthOpen(true)} 
              className="btn-primary unauth-cta-btn"
            >
              Get Started / Sign In
            </button>
          </div>
        </section>
      )}

      {/* Diagnostics */}
      <ServiceStatus 
        backendData={backendData} 
        isChecking={isChecking} 
        onRefresh={checkHealth} 
      />

      <ArchitectureOverview backendData={backendData} />
    </main>
  );
}
