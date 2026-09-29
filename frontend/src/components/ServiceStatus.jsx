import React from 'react';
import { Layout, Server, Database, HardDrive, CheckCircle2, AlertCircle, RefreshCw } from 'lucide-react';

export default function ServiceStatus({ backendData, isChecking, onRefresh }) {
  const backendOnline = backendData && backendData.status === 'healthy';

  const services = [
    {
      name: 'React Frontend',
      serviceId: 'frontend',
      role: 'Web UI & Dashboard',
      network: 'frontend_net',
      port: '5173 (Host)',
      status: 'online',
      statusText: 'Active',
      icon: <Layout size={22} color="#38bdf8" />,
      iconBg: 'rgba(56, 189, 248, 0.15)',
    },
    {
      name: 'Flask Backend',
      serviceId: 'backend',
      role: 'API Gateway & Services',
      network: 'frontend_net, backend_net',
      port: '5000 (Host)',
      status: backendOnline ? 'online' : (backendData ? 'error' : 'standby'),
      statusText: backendOnline ? 'Healthy' : (backendData ? 'Unhealthy' : 'Checking...'),
      icon: <Server size={22} color="#34d399" />,
      iconBg: 'rgba(52, 211, 153, 0.15)',
    },
    {
      name: 'PostgreSQL DB',
      serviceId: 'db',
      role: 'Metadata & File Catalog',
      network: 'backend_net',
      port: '5432 (Internal)',
      status: backendOnline ? 'online' : 'standby',
      statusText: backendOnline ? 'Connected' : 'Isolated Network',
      icon: <Database size={22} color="#818cf8" />,
      iconBg: 'rgba(129, 140, 248, 0.15)',
    },
    {
      name: 'MinIO Storage',
      serviceId: 'minio',
      role: 'Object Storage & Blobs',
      network: 'backend_net',
      port: '9000 (API) / 9001 (Console)',
      status: backendOnline ? 'online' : 'standby',
      statusText: backendOnline ? 'Connected' : 'Isolated Network',
      icon: <HardDrive size={22} color="#fbbf24" />,
      iconBg: 'rgba(251, 191, 36, 0.15)',
    },
  ];

  return (
    <div>
      <div className="section-title">
        <h2>
          <span>Docker Compose Services</span>
          <span style={{ fontSize: '0.85rem', color: 'var(--text-muted)', fontWeight: 'normal' }}>
            (4 Services Configured)
          </span>
        </h2>
        <button 
          onClick={onRefresh} 
          disabled={isChecking}
          className="btn-secondary"
          style={{ padding: '0.4rem 0.85rem', fontSize: '0.8rem' }}
        >
          <RefreshCw size={14} className={isChecking ? 'spin' : ''} />
          <span>{isChecking ? 'Checking...' : 'Re-check Status'}</span>
        </button>
      </div>

      <div className="services-grid">
        {services.map((svc) => (
          <div key={svc.serviceId} className="service-card">
            <div>
              <div className="service-card-top">
                <div className="service-icon-box" style={{ background: svc.iconBg }}>
                  {svc.icon}
                </div>
                <span className={`service-badge ${svc.status === 'online' ? 'badge-online' : (svc.status === 'error' ? 'badge-error' : 'badge-standby')}`}>
                  {svc.status === 'online' ? <CheckCircle2 size={12} /> : <AlertCircle size={12} />}
                  {svc.statusText}
                </span>
              </div>
              <h3 className="service-name">{svc.name}</h3>
              <p className="service-desc">{svc.role}</p>
            </div>

            <div className="service-meta">
              <div className="meta-row">
                <span>Service:</span>
                <span className="meta-val">{svc.serviceId}</span>
              </div>
              <div className="meta-row">
                <span>Network:</span>
                <span className="meta-val">{svc.network}</span>
              </div>
              <div className="meta-row">
                <span>Port:</span>
                <span className="meta-val">{svc.port}</span>
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
