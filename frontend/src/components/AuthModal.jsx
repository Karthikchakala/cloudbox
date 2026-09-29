import React, { useState } from 'react';
import { Lock, Mail, User, ArrowRight, ShieldCheck, AlertCircle, X } from 'lucide-react';
import { loginUser, registerUser } from '../services/api';

export default function AuthModal({ isOpen, onClose, onAuthSuccess }) {
  const [tab, setTab] = useState('login'); // 'login' | 'register'
  const [username, setUsername] = useState('');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  if (!isOpen) return null;

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');
    setLoading(true);

    try {
      if (tab === 'login') {
        const res = await loginUser(email, password);
        if (res.ok) {
          onAuthSuccess(res.data.user);
          onClose();
        } else {
          setError(res.error);
        }
      } else {
        if (!username.trim()) {
          setError('Username is required.');
          setLoading(false);
          return;
        }
        if (password.length < 8) {
          setError('Password must be at least 8 characters long.');
          setLoading(false);
          return;
        }
        const res = await registerUser(username, email, password);
        if (res.ok) {
          onAuthSuccess(res.data.user);
          onClose();
        } else {
          setError(res.error);
        }
      }
    } catch (err) {
      setError('An unexpected error occurred. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="modal-overlay">
      <div className="modal-card">
        <button className="modal-close" onClick={onClose} aria-label="Close modal">
          <X size={20} />
        </button>

        <div className="auth-header">
          <div className="auth-icon-box">
            <ShieldCheck size={26} color="#38bdf8" />
          </div>
          <h2>{tab === 'login' ? 'Sign In to CloudBox' : 'Create an Account'}</h2>
          <p>
            {tab === 'login' 
              ? 'Access your private files, persistent volumes, and object storage.' 
              : 'Deploy your personal self-hosted cloud storage space.'}
          </p>
        </div>

        <div className="auth-tabs">
          <button 
            type="button"
            className={`auth-tab ${tab === 'login' ? 'active' : ''}`}
            onClick={() => { setTab('login'); setError(''); }}
          >
            Sign In
          </button>
          <button 
            type="button"
            className={`auth-tab ${tab === 'register' ? 'active' : ''}`}
            onClick={() => { setTab('register'); setError(''); }}
          >
            Register
          </button>
        </div>

        {error && (
          <div className="alert-error">
            <AlertCircle size={18} />
            <span>{error}</span>
          </div>
        )}

        <form onSubmit={handleSubmit} className="auth-form">
          {tab === 'register' && (
            <div className="form-group">
              <label htmlFor="auth-username">Username</label>
              <div className="input-with-icon">
                <User size={18} className="field-icon" />
                <input 
                  id="auth-username"
                  type="text" 
                  placeholder="e.g. dev_architect" 
                  value={username}
                  onChange={(e) => setUsername(e.target.value)}
                  required
                />
              </div>
            </div>
          )}

          <div className="form-group">
            <label htmlFor="auth-email">Email Address</label>
            <div className="input-with-icon">
              <Mail size={18} className="field-icon" />
              <input 
                id="auth-email"
                type="email" 
                placeholder="name@example.com" 
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                required
              />
            </div>
          </div>

          <div className="form-group">
            <label htmlFor="auth-password">Password</label>
            <div className="input-with-icon">
              <Lock size={18} className="field-icon" />
              <input 
                id="auth-password"
                type="password" 
                placeholder="Minimum 8 characters" 
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                required
              />
            </div>
          </div>

          <button 
            type="submit" 
            className="btn-primary auth-submit-btn" 
            disabled={loading}
          >
            <span>{loading ? 'Processing...' : (tab === 'login' ? 'Sign In' : 'Create Account')}</span>
            <ArrowRight size={16} />
          </button>
        </form>
      </div>
    </div>
  );
}
