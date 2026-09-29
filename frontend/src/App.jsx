import React, { useState, useEffect } from 'react';
import Header from './components/Header';
import Dashboard from './pages/Dashboard';
import Footer from './components/Footer';
import { getCurrentUser, setAuthToken } from './services/api';

export default function App() {
  const [user, setUser] = useState(null);
  const [isAuthOpen, setIsAuthOpen] = useState(false);

  useEffect(() => {
    async function loadUser() {
      const res = await getCurrentUser();
      if (res.ok) {
        setUser(res.data);
      }
    }
    loadUser();
  }, []);

  const handleLogout = () => {
    setAuthToken(null);
    setUser(null);
  };

  return (
    <div className="app-container">
      <Header 
        user={user} 
        onLogout={handleLogout} 
        onOpenAuth={() => setIsAuthOpen(true)} 
      />
      <Dashboard 
        user={user} 
        setUser={setUser} 
        isAuthOpen={isAuthOpen} 
        setIsAuthOpen={setIsAuthOpen} 
      />
      <Footer />
    </div>
  );
}
