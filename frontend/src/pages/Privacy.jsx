import React, { useEffect } from "react";
import { Link } from "react-router-dom";
import "../App.css";

export default function Privacy() {
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
          <div className="status-badge slide-up-stagger-1">🔒 Legal Notice</div>
          <h2 className="section-title slide-up-stagger-2">Privacy <span className="purple-text" style={{ background: 'rgba(124,58,237,0.05)', padding: '0 10px', borderRadius: '12px' }}>Policy</span></h2>
          <p className="section-subtitle slide-up-stagger-3">How we protect, encrypt, and manage your sensitive biomarker data.</p>
        </div>

        <div className="bento-card slide-up-stagger-4" style={{ textAlign: 'left', margin: '0 auto', maxWidth: '800px', padding: '60px', userSelect: 'auto', WebkitUserSelect: 'auto' }}>
            <h3 style={{ fontSize: '1.4rem', marginBottom: '20px', color: 'var(--deep-slate)', fontFamily: 'Outfit, sans-serif' }}>1. Data Collection</h3>
             <p style={{ marginBottom: '20px', lineHeight: '1.8' }}>We collect only the minimum necessary actionable biomarker and metabolic data required to power the AI-NutriCare diagnostic engine. This includes user-uploaded laboratory tests (specifically JSON or PDF OCR artifacts) and explicit intake questionnaires.</p>

             <h3 style={{ fontSize: '1.4rem', marginBottom: '20px', color: 'var(--deep-slate)', fontFamily: 'Outfit, sans-serif' }}>2. Data Encryption & Security (Web3 Standard)</h3>
             <p style={{ marginBottom: '20px', lineHeight: '1.8' }}>Your personal health information (PHI) never exists in plaintext within our operational databases. We utilize AES-256 encryption at rest and TLS 1.3 in transit. Your unique identity is abstracted and containerized separately from analytical machine learning pipelines, ensuring anonymity in population modeling.</p>

             <h3 style={{ fontSize: '1.4rem', marginBottom: '20px', color: 'var(--deep-slate)', fontFamily: 'Outfit, sans-serif' }}>3. Third-Party Sharing</h3>
             <p style={{ marginBottom: '20px', lineHeight: '1.8' }}>AI-NutriCare does not, and will never, sell or distribute identifying clinical data to third-party advertisers, insurance agencies, or pharmaceutical entities. Aggregated, fully anonymized metadata may be utilized strictly internally to improve the accuracy of our baseline ML models.</p>

             <h3 style={{ fontSize: '1.4rem', marginBottom: '20px', color: 'var(--deep-slate)', fontFamily: 'Outfit, sans-serif' }}>4. Your Rights to Erasure</h3>
             <p style={{ marginBottom: '0px', lineHeight: '1.8' }}>Under GDPR and equivalent federal statutes, you maintain the absolute right to purge your entire clinical record from our ledgers. The 'Delete Account' function in the Dashboard performs a hard-delete cascade, unrecoverably wiping all diagnostic histories.</p>
        </div>
      </div>
    </div>
  );
}
