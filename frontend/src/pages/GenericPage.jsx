import React, { useEffect } from "react";
import { Link, useLocation } from "react-router-dom";
import "../App.css";

export default function GenericPage() {
  useEffect(() => { window.scrollTo(0, 0); }, []);
  const location = useLocation();
  const pathTitle = location.pathname.replace('/', '').replace(/-/g, ' ');
  const displayTitle = pathTitle.charAt(0).toUpperCase() + pathTitle.slice(1);

  return (
    <div className="landing-wrapper" style={{ overflowX: 'hidden', minHeight: '100vh', display: 'flex', flexDirection: 'column' }}>
      <nav className="navbar">
        <div className="nav-container">
          <Link to="/" className="logo" style={{ textDecoration: 'none' }}>AI-<span>NutriCare</span></Link>
          <div className="nav-menu" style={{ display: 'flex', gap: '15px' }}>
             <Link to="/" className="clay-btn-secondary" style={{ textDecoration: 'none', padding: '8px 20px' }}>← Home</Link>
          </div>
        </div>
      </nav>

      <div className="main-container" style={{ padding: '160px 24px 80px', position: 'relative', flex: 1 }}>
         <div style={{
          content: '""', position: 'absolute', width: '600px', height: '600px', borderRadius: '50%', filter: 'blur(120px)', zIndex: -1, background: 'rgba(124, 58, 237, 0.15)', top: '-100px', right: '-100px'
        }} />

        <div className="section-header-centered fade-in" style={{ marginBottom: '60px' }}>
          <h2 className="section-title slide-up-stagger-2" style={{ textTransform: 'capitalize' }}>{displayTitle}</h2>
          <p className="section-subtitle slide-up-stagger-3">This page is currently under structural construction.</p>
        </div>

        <div className="bento-card slide-up-stagger-4" style={{ textAlign: 'center', margin: '0 auto', maxWidth: '800px', padding: '60px' }}>
             <div className="floating-loader" style={{ width: '40px', height: '40px', border: '3px solid var(--lavender-light)', borderTop: '3px solid var(--lavender)', borderRadius: '50%', animation: 'spin 1.5s linear infinite', margin: '0 auto 20px' }} />
             <p style={{ color: 'var(--text-gray)' }}>Our engineering team is currently formatting the complete documentation for the {displayTitle} portal. Please check back shortly.</p>
        </div>
      </div>
    </div>
  );
}
