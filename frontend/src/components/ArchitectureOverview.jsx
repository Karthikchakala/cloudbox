import React from 'react';
import { Network, Database, Shield, Layers } from 'lucide-react';

export default function ArchitectureOverview({ backendData }) {
  return (
    <div className="topology-card">
      <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '0.5rem' }}>
        <Network size={20} color="#38bdf8" />
        <h3 style={{ fontSize: '1.2rem', fontWeight: 700 }}>Network Topology & Volumes</h3>
      </div>
      <p style={{ color: 'var(--text-secondary)', fontSize: '0.9rem', marginBottom: '1.25rem' }}>
        Dual-bridge network isolation ensuring database and object storage layers remain shielded from public direct exposure.
      </p>

      <div className="networks-grid">
        <div className="network-box">
          <div className="network-header">
            <Layers size={18} color="#60a5fa" />
            <span style={{ color: '#93c5fd' }}>frontend_net (Bridge)</span>
          </div>
          <p style={{ color: 'var(--text-secondary)', fontSize: '0.8rem', marginBottom: '0.75rem' }}>
            Handles browser-to-backend API communication and client UI distribution.
          </p>
          <div className="network-tags">
            <span className="tag-node">frontend (React:5173)</span>
            <span className="tag-node">backend (Flask:5000)</span>
          </div>
        </div>

        <div className="network-box">
          <div className="network-header">
            <Shield size={18} color="#34d399" />
            <span style={{ color: '#6ee7b7' }}>backend_net (Bridge)</span>
          </div>
          <p style={{ color: 'var(--text-secondary)', fontSize: '0.8rem', marginBottom: '0.75rem' }}>
            Secure private data plane for API transactions and binary storage streams.
          </p>
          <div className="network-tags">
            <span className="tag-node">backend</span>
            <span className="tag-node">db (PostgreSQL:5432)</span>
            <span className="tag-node">minio (S3:9000)</span>
          </div>
        </div>
      </div>

      <div style={{ marginTop: '1.5rem' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '0.5rem' }}>
          <Database size={18} color="#fbbf24" />
          <h4 style={{ fontSize: '1rem', fontWeight: 600 }}>Persistent Volumes</h4>
        </div>
        <div className="networks-grid" style={{ marginTop: '0.5rem' }}>
          <div className="network-box">
            <span style={{ fontWeight: 600, color: '#fcd34d', fontSize: '0.85rem' }}>postgres_data</span>
            <p style={{ color: 'var(--text-secondary)', fontSize: '0.8rem', marginTop: '4px' }}>
              Mount: <code>/var/lib/postgresql/data</code>
            </p>
          </div>
          <div className="network-box">
            <span style={{ fontWeight: 600, color: '#fcd34d', fontSize: '0.85rem' }}>minio_data</span>
            <p style={{ color: 'var(--text-secondary)', fontSize: '0.8rem', marginTop: '4px' }}>
              Mount: <code>/data</code>
            </p>
          </div>
        </div>
      </div>

      {backendData && (
        <div style={{ marginTop: '1.5rem' }}>
          <div className="diag-console">
            <div className="diag-header">
              <span>LIVE HEALTH RESPONSE (GET /health)</span>
              <span>200 OK</span>
            </div>
            <pre className="diag-body">{JSON.stringify(backendData, null, 2)}</pre>
          </div>
        </div>
      )}
    </div>
  );
}
