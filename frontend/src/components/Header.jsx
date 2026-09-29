import React from 'react';
import { Cloud, Server, Database, LogOut, User as UserIcon } from 'lucide-react';

export default function Header({ user, onLogout, onOpenAuth }) {
  return (
    <header className="header">
      <div className="brand">
        <div className="brand-icon">
          <Cloud size={24} />
        </div>
        <div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <span className="brand-title">CloudBox</span>
            <span className="brand-badge">Phase 2 Active</span>
          </div>
          <p style={{ fontSize: '0.8rem', color: 'var(--text-secondary)' }}>
            Self-Hosted Object Storage & File Catalog
          </p>
        </div>
      </div>

      <div className="header-links">
        <a 
          href="http://localhost:5000/health" 
          target="_blank" 
          rel="noreferrer" 
          className="btn-secondary"
          title="Inspect Flask Backend Health Probe"
        >
          <Server size={15} />
          <span>API Health</span>
        </a>
        <a 
          href="http://localhost:9001" 
          target="_blank" 
          rel="noreferrer" 
          className="btn-secondary"
          title="MinIO Object Storage Console"
        >
          <Database size={15} />
          <span>MinIO Console</span>
        </a>

        {user ? (
          <div className="user-profile-widget">
            <div className="user-avatar-badge">
              <UserIcon size={14} />
              <span className="user-name-text">{user.username}</span>
            </div>
            <button 
              onClick={onLogout} 
              className="btn-secondary btn-logout"
              title="Sign Out"
            >
              <LogOut size={15} />
              <span>Logout</span>
            </button>
          </div>
        ) : (
          <button 
            onClick={onOpenAuth} 
            className="btn-primary"
          >
            Sign In / Register
          </button>
        )}
      </div>
    </header>
  );
}
