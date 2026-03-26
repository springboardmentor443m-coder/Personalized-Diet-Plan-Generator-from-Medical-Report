import { Link } from "react-router-dom";
import React from "react";
import "../App.css";

export default function Landing() {
  return (
    <div className="landing-wrapper">
      {/* NAVBAR */}
      <nav className="navbar">
        <div className="nav-container">
          <div className="logo">AI-<span>NutriCare</span></div>
          <div className="nav-menu">
            <a href="#features">Features</a>
            <a href="#how">How it Works</a>
            <a href="#feedback">Testimonials</a>
          </div>
          <div className="nav-actions">
            <Link to="/login" className="btn-login">Login</Link>
            <Link to="/signup" className="clay-btn-primary">Sign Up</Link>
          </div>
        </div>
      </nav>

      {/* HERO SECTION */}
      <header className="hero">
        <div className="main-container hero-flex">
          <div className="hero-content">
            <div className="status-badge slide-up-stagger-1">✨ Next-Gen AI Nutrition</div>
            <h1 className="slide-up-stagger-2">
              Your Biomarkers, <br />
              <span className="purple-text" style={{ background: 'rgba(124,58,237,0.05)', padding: '0 10px', borderRadius: '12px' }}>Fully Optimized.</span>
            </h1>
            <p className="hero-description slide-up-stagger-3">
              Upload your medical reports and let our clinical-grade AI 
              engineer a diet plan tailored specifically to your blood chemistry.
            </p>
            <div className="hero-cta-group slide-up-stagger-4">
              <Link to="/signup" className="clay-btn-primary">Get Started Now</Link>
              <Link to="/sample-plan" className="clay-btn-secondary" style={{ textDecoration: 'none', display: 'inline-block' }}>
                View Sample Plan
              </Link>
            </div>
          </div>

          <div className="hero-graphic fade-in">
            <img src="/claymorphism_hero.png" alt="Claymorphism Medical AI Dashboard and Capsule" className="float-animation" />
          </div>
        </div>
      </header>

      {/* TRUST MARQUEE */}
      <div className="brands-banner">
        <div className="brands-track">
          <span className="brand-item">Verified Clinical Integrity</span>
          <span className="brand-item">HIPAA Compliant</span>
          <span className="brand-item">Powered by LLMs</span>
          <span className="brand-item">Web3 Security Standard</span>
          <span className="brand-item">End-to-end Encrypted</span>
          {/* Duplicates for infinite scroll effect */}
          <span className="brand-item">Verified Clinical Integrity</span>
          <span className="brand-item">HIPAA Compliant</span>
          <span className="brand-item">Powered by LLMs</span>
          <span className="brand-item">Web3 Security Standard</span>
          <span className="brand-item">End-to-end Encrypted</span>
        </div>
      </div>

      {/* FEATURE SPOTLIGHT 1: ML ANALYSIS */}
      <section id="features" className="spotlight-section">
        <div className="main-container spotlight-flex">
          <div className="spotlight-text">
            <span className="spotlight-tag">Neural Architecture</span>
            <h2>Machine Learning mapped specifically to your DNA.</h2>
            <p>
              We cross-reference every individual biomarker against millions of global, peer-reviewed clinical data points to establish a perfect nutritional alignment for your unique physical structure.
            </p>
            <ul className="feature-list">
              <li><div className="check-icon">✓</div> High-dimensional blood analysis</li>
              <li><div className="check-icon">✓</div> Real-time medical cross-referencing</li>
              <li><div className="check-icon">✓</div> Advanced lipid tracking metrics</li>
            </ul>
          </div>
          <div className="spotlight-image slide-up">
            <img src="/3d_dna_analysis.png" alt="3D Double Helix DNA glowing" className="float-animation" />
          </div>
        </div>
      </section>

      {/* FEATURE SPOTLIGHT 2: SMART OCR */}
      <section className="spotlight-section">
        <div className="main-container spotlight-flex reverse">
          <div className="spotlight-text">
            <span className="spotlight-tag">Smart Vision OCR</span>
            <h2>Instant Extraction from any Medical Document.</h2>
            <p>
              Forget manual data entry. Our proprietary Smart Vision system scans standard PDFs or crumpled clinical JPG files, flawlessly extracting vital metric data in milliseconds.
            </p>
            <ul className="feature-list">
              <li><div className="check-icon">✓</div> Support for JPG, PNG, and PDF</li>
              <li><div className="check-icon">✓</div> 99.8% Medical Terminology Accuracy</li>
              <li><div className="check-icon">✓</div> Automatic anomaly highlighting</li>
            </ul>
          </div>
          <div className="spotlight-image fade-in">
            <img src="/3d_medical_document.png" alt="3D Medical Document illuminated" style={{ animationDelay: '1s' }} className="float-animation" />
          </div>
        </div>
      </section>

      {/* BENTO BOX GRID: SECONDARY FEATURES */}
      <section id="how" className="bento-section">
        <div className="main-container">
          <div className="section-header-centered">
            <h2 className="section-title">Engineered for Trust</h2>
            <p className="section-subtitle">We handle your medical data with uncompromising web3 standards.</p>
          </div>
          
          <div className="bento-grid">
            <div className="bento-card bento-large">
              <h3>Military-Grade Encryption</h3>
              <p>Your blood metrics and personal data never leave our secure, containerized enclave. AES-256 encryption at rest and in transit.</p>
            </div>
            <div className="bento-card">
               <h3>Dynamic Updating</h3>
               <p>As your biomarkers shift month-over-month, your generated diet plans intelligently adapt.</p>
            </div>
            <div className="bento-card">
               <h3>Export Anywhere</h3>
               <p>Instantly download PDF briefs formatted exactly how your primary care physician prefers to read them.</p>
            </div>
            <div className="bento-card bento-large" style={{ background: 'var(--lavender)', color: 'white', borderColor: 'transparent' }}>
               <h3 style={{ color: 'white' }}>Start your optimization.</h3>
               <p style={{ color: 'rgba(255,255,255,0.8)', marginBottom: '30px' }}>Join thousands of users upgrading their biology through AI-driven nutrition.</p>
               <div>
                  <Link to="/signup" className="clay-btn-secondary" style={{ display: 'inline-block', textDecoration: 'none' }}>Access Dashboard</Link>
               </div>
            </div>
          </div>
        </div>
      </section>

      {/* USER FEEDBACK SECTION */}
      <section id="feedback" className="section-padding feedback-section">
        <div className="main-container">
          <h2 className="section-title">What Our Users Say</h2>
          <div className="feedback-grid">
            <div className="feedback-card">
              <div className="stars">⭐⭐⭐⭐⭐</div>
              <p>"Finally, a way to actually understand what my blood work means. My energy levels have doubled."</p>
              <div className="user-info">
                <strong>Sarah Jenkins</strong>
                <span>Verified User</span>
              </div>
            </div>
            <div className="feedback-card">
              <div className="stars">⭐⭐⭐⭐⭐</div>
              <p>"The OCR technology is flawless. I uploaded a scan and it gave me a detailed meal plan instantly."</p>
              <div className="user-info">
                <strong>Marcus Chen</strong>
                <span>Software Engineer</span>
              </div>
            </div>
            <div className="feedback-card">
              <div className="stars">⭐⭐⭐⭐⭐</div>
              <p>"As someone with high cholesterol, this assistant is a lifesaver. No more generic advice."</p>
              <div className="user-info">
                <strong>Elena Rodriguez</strong>
                <span>Health Enthusiast</span>
              </div>
            </div>
          </div>
        </div>
      </section>
    </div>
  );
}