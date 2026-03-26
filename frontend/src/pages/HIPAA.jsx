import React, { useEffect } from "react";
import { Link } from "react-router-dom";
import "../App.css";

export default function HIPAA() {
  useEffect(() => { window.scrollTo(0, 0); }, []);

  return (
    <div className="landing-wrapper" style={{ overflowX: 'hidden' }}>
      <nav className="navbar">
        <div className="nav-container">
          <Link to="/" className="logo" style={{ textDecoration: 'none' }}>AI-<span>NutriCare</span></Link>
          <div className="nav-menu" style={{ display: 'flex', gap: '15px' }}>
             <Link to="/" className="clay-btn-secondary" style={{ textDecoration: 'none', padding: '8px 20px' }}>← Home</Link>
          </div>
        </div>
      </nav>

      <div className="main-container" style={{ padding: '160px 24px 80px', position: 'relative' }}>
         <div style={{
          content: '""', position: 'absolute', width: '600px', height: '600px', borderRadius: '50%', filter: 'blur(120px)', zIndex: -1, background: 'rgba(124, 58, 237, 0.15)', top: '-100px', right: '-100px'
        }} />

        <div className="section-header-centered fade-in" style={{ marginBottom: '60px' }}>
          <div className="status-badge slide-up-stagger-1">🏥 Security Notice</div>
          <h2 className="section-title slide-up-stagger-2">HIPAA <span className="purple-text" style={{ background: 'rgba(124,58,237,0.05)', padding: '0 10px', borderRadius: '12px' }}>Compliance</span></h2>
          <p className="section-subtitle slide-up-stagger-3">Details regarding our commitment to Federal Healthcare Information Security.</p>
        </div>

        <div className="bento-card slide-up-stagger-4" style={{ textAlign: 'left', margin: '0 auto', maxWidth: '800px', padding: '60px', userSelect: 'auto', WebkitUserSelect: 'auto' }}>
            <h3 style={{ fontSize: '1.4rem', marginBottom: '20px', color: 'var(--deep-slate)', fontFamily: 'Outfit, sans-serif' }}>1. Federal Compliance Framework</h3>
             <p style={{ marginBottom: '20px', lineHeight: '1.8' }}>AI-NutriCare adheres strictly to the Health Insurance Portability and Accountability Act of 1996 (HIPAA) Security Rule. We implement comprehensive administrative, physical, and technical safeguards to ensure the confidentiality, integrity, and availability of all electronic protected health information (ePHI) we create, receive, maintain, or transmit.</p>

             <h3 style={{ fontSize: '1.4rem', marginBottom: '20px', color: 'var(--deep-slate)', fontFamily: 'Outfit, sans-serif' }}>2. Business Associate Agreements (BAA)</h3>
             <p style={{ marginBottom: '20px', lineHeight: '1.8' }}>For our active B2B clinical partners, AI-NutriCare operates as a fully auditable Business Associate. We provide pre-executed BAAs ensuring zero-knowledge cloud architectures for patient diagnosis pipelines.</p>

             <h3 style={{ fontSize: '1.4rem', marginBottom: '20px', color: 'var(--deep-slate)', fontFamily: 'Outfit, sans-serif' }}>3. Access Controls</h3>
             <p style={{ marginBottom: '0px', lineHeight: '1.8' }}>Strict Role-Based Access Control (RBAC) matrices prevent unauthorized internal viewing of identifiable lab results and blood work. All database interactions are uniquely authenticated and irrepudiably logged for forensic auditing.</p>
        </div>
      </div>
    </div>
  );
}
