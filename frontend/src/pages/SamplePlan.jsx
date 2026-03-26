import React from "react";
import { Link } from "react-router-dom";
import "../App.css";

export default function SamplePlan() {
  return (
    <div className="sample-page landing-wrapper" style={{ overflowX: 'hidden' }}>
      {/* FLOATING NAVBAR */}
      <nav className="navbar">
        <div className="nav-container">
          <Link to="/" className="logo" style={{ textDecoration: 'none' }}>AI-<span>NutriCare</span></Link>
          <div className="nav-menu" style={{ display: 'flex', gap: '15px' }}>
             <Link to="/" className="clay-btn-secondary" style={{ textDecoration: 'none', padding: '8px 20px' }}>← Home</Link>
             <Link to="/signup" className="clay-btn-primary" style={{ textDecoration: 'none', padding: '8px 20px' }}>Start Free</Link>
          </div>
        </div>
      </nav>

      <div className="main-container" style={{ padding: '160px 24px 80px', position: 'relative' }}>
         {/* AMBIENT GLOWS */}
        <div style={{
          content: '""', position: 'absolute', width: '600px', height: '600px', borderRadius: '50%', filter: 'blur(120px)', zIndex: -1, background: 'rgba(124, 58, 237, 0.15)', top: '-100px', right: '-100px'
        }} />

        <div className="section-header-centered fade-in" style={{ marginBottom: '60px' }}>
          <div className="status-badge slide-up-stagger-1">🩺 Clinical Output Example</div>
          <h2 className="section-title slide-up-stagger-2">Diagnostic <span className="purple-text" style={{ background: 'rgba(124,58,237,0.05)', padding: '0 10px', borderRadius: '12px' }}>Analysis</span></h2>
          <p className="section-subtitle slide-up-stagger-3">An exact preview of how our medical AI interprets standard blood chemistry.</p>
        </div>

        <div className="sample-dashboard slide-up-stagger-4">
          {/* Top Stats Grid */}
          <div className="dashboard-grid">
            <div className="clay-card">
              <h3 style={{ fontSize: '1.4rem', marginBottom: '20px', color: 'var(--deep-slate)', fontFamily: 'Outfit, sans-serif' }}>Primary Biomarkers</h3>
              <div className="report-stat">
                <span style={{ color: 'var(--text-gray)' }}>Blood Glucose</span>
                <span className="stat-pill warning">110 mg/dL (High)</span>
              </div>
              <div className="report-stat">
                <span style={{ color: 'var(--text-gray)' }}>Vitamin D</span>
                <span className="stat-pill success">32 ng/mL (Optimal)</span>
              </div>
              <div className="report-stat" style={{ borderBottom: 'none' }}>
                <span style={{ color: 'var(--text-gray)' }}>Iron (Ferritin)</span>
                <span className="stat-pill warning">18 ng/mL (Low)</span>
              </div>
            </div>

            <div className="clay-card">
              <h3 style={{ fontSize: '1.4rem', marginBottom: '15px', color: 'var(--deep-slate)', fontFamily: 'Outfit, sans-serif' }}>AI Risk Assessment</h3>
              <div className="ai-insight-box">
                <strong style={{ display: 'block', marginBottom: '8px', color: 'var(--lavender)' }}>Potential Condition: Pre-Diabetes Risk</strong>
                <p style={{ fontSize: '0.95rem' }}>Blood glucose levels are currently in the pre-diabetic range. Early intervention is recommended.</p>
              </div>
              <div className="ai-insight-box" style={{marginTop: '15px'}}>
                <strong style={{ display: 'block', marginBottom: '8px', color: 'var(--lavender)' }}>Potential Condition: Anemia Risk</strong>
                <p style={{ fontSize: '0.95rem' }}>Low iron levels may lead to fatigue and decreased cognitive function.</p>
              </div>
            </div>
          </div>

          {/* BENTO GRID DIET PLAN */}
          <div className="bento-section" style={{ marginTop: '60px', padding: '60px 0', background: 'transparent', boxShadow: 'none' }}>
            <h3 className="section-title" style={{fontSize: '2rem', marginBottom: '40px'}}>Personalized <span className="purple-text">Nutrition Roadmap</span></h3>
            
            <div className="bento-grid">
              <div className="bento-card bento-large">
                <div style={{ fontSize: '3rem', marginBottom: '20px' }}>🥗</div>
                <h3 style={{ marginBottom: '15px' }}>Therapeutic Foods</h3>
                <p style={{ marginBottom: '20px' }}>Based on your iron and glucose readings, focus entirely on these nutrient-dense whole foods to optimize markers.</p>
                <ul className="feature-list" style={{ marginTop: 'auto', marginBottom: 0 }}>
                  <li><div className="check-icon" style={{ width: '24px', height: '24px', fontSize: '12px' }}>✓</div> Leafy Greens (Spinach, Kale)</li>
                  <li><div className="check-icon" style={{ width: '24px', height: '24px', fontSize: '12px' }}>✓</div> Lean Proteins (Lentils, Tofu)</li>
                  <li><div className="check-icon" style={{ width: '24px', height: '24px', fontSize: '12px' }}>✓</div> Complex Carbs (Quinoa, Oats)</li>
                </ul>
              </div>

              <div className="bento-card">
                <div style={{ fontSize: '3rem', marginBottom: '20px' }}>🚫</div>
                <h3>Avoid Entirely</h3>
                <p style={{ marginBottom: '20px' }}>These compounds directly exacerbate your current biomarker imbalances.</p>
                <ul className="feature-list" style={{ marginBottom: 0 }}>
                  <li style={{ color: '#ef4444' }}>• Refined Sugars & Sodas</li>
                  <li style={{ color: '#ef4444' }}>• White Bread & Pasta</li>
                  <li style={{ color: '#ef4444' }}>• High-Sodium Snacks</li>
                </ul>
              </div>

              <div className="bento-card" style={{ background: 'var(--lavender)', color: 'white' }}>
                <div style={{ fontSize: '3rem', marginBottom: '20px' }}>💊</div>
                <h3 style={{ color: 'white' }}>Clinical Supplements</h3>
                <p style={{ color: 'rgba(255,255,255,0.9)', marginBottom: '20px' }}>Required daily additions to bridge your biological gaps.</p>
                <ul className="feature-list" style={{ color: 'white', marginBottom: 0 }}>
                  <li style={{ color: 'white' }}>• Iron (Chewable or Pill)</li>
                  <li style={{ color: 'white' }}>• Vitamin C (for absorption)</li>
                </ul>
              </div>

              <div className="bento-card bento-large" style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', padding: 0, overflow: 'hidden', height: '100%', position: 'relative' }}>
                <img src="/3d_vitamins.png" alt="3D Vitamins" className="float-animation" style={{ position: 'absolute', width: '100%', height: '100%', objectFit: 'cover', objectPosition: 'center', filter: 'drop-shadow(10px 20px 30px rgba(124,58,237,0.15))' }} />
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}