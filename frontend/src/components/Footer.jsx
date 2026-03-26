import React from 'react';
import { Link } from 'react-router-dom';

const Footer = () => {
  // Helper to ensure pages open at the top
  const scrollToTop = () => {
    window.scrollTo({ top: 0, behavior: 'smooth' });
  };

  return (
    <footer className="site-footer">
      <div className="main-container footer-content">
        <div className="footer-brand-section">
          <h2>AI-<span>NutriCare</span></h2>
          <p>Clinical-grade nutrition optimization powered by advanced blood biomarker analysis.</p>
          <div className="social-links" style={{ display: 'flex', gap: '15px', marginTop: '20px' }}>
             {/* Social Media SVG Placeholders */}
             <a href="#" aria-label="Twitter">
               <svg style={{ width: '24px', height: '24px', fill: 'var(--text-gray)' }} viewBox="0 0 24 24"><path d="M23 3a10.9 10.9 0 0 1-3.14 1.53 4.48 4.48 0 0 0-7.86 3v1A10.66 10.66 0 0 1 3 4s-4 9 5 13a11.64 11.64 0 0 1-7 2c9 5 20 0 20-11.5a4.5 4.5 0 0 0-.08-.83A7.72 7.72 0 0 0 23 3z"></path></svg>
             </a>
             <a href="#" aria-label="LinkedIn">
               <svg style={{ width: '24px', height: '24px', fill: 'var(--text-gray)' }} viewBox="0 0 24 24"><path d="M16 8a6 6 0 0 1 6 6v7h-4v-7a2 2 0 0 0-2-2 2 2 0 0 0-2 2v7h-4v-7a6 6 0 0 1 6-6z"></path><rect x="2" y="9" width="4" height="12"></rect><circle cx="4" cy="4" r="2"></circle></svg>
             </a>
             <a href="#" aria-label="Instagram">
               <svg style={{ width: '24px', height: '24px', fill: 'none', stroke: 'var(--text-gray)', strokeWidth: '2', strokeLinecap: 'round', strokeLinejoin: 'round' }} viewBox="0 0 24 24"><rect x="2" y="2" width="20" height="20" rx="5" ry="5"></rect><path d="M16 11.37A4 4 0 1 1 12.63 8 4 4 0 0 1 16 11.37z"></path><line x1="17.5" y1="6.5" x2="17.51" y2="6.5"></line></svg>
             </a>
          </div>
        </div>
        
        <div className="footer-links-wrapper">
          <div className="footer-col">
            <h4>Company</h4>
            <Link to="/about" onClick={scrollToTop}>About</Link>
            <Link to="/contact" onClick={scrollToTop}>Contact Us</Link>
            <Link to="/careers" onClick={scrollToTop}>Careers</Link>
          </div>
          <div className="footer-col">
            <h4>Legal</h4>
            <Link to="/privacy" onClick={scrollToTop}>Privacy Policy</Link>
            <Link to="/terms" onClick={scrollToTop}>Terms of Service</Link>
          </div>
          <div className="footer-col">
            <h4>Certifications</h4>
            <Link to="/legitscript" onClick={scrollToTop}>Legit Script</Link>
            <Link to="/hipaa" onClick={scrollToTop}>HIPAA</Link>
          </div>
          <div className="footer-col">
            <h4>Support</h4>
            <Link to="/faq" onClick={scrollToTop}>FAQ</Link>
            <Link to="/feedback" onClick={scrollToTop}>Feedback</Link>
            <Link to="/organizations" onClick={scrollToTop}>For Organizations</Link>
          </div>
        </div>
      </div>
      
      <div className="footer-bottom">
        <div className="main-container footer-bottom-flex">
          <p>&copy; 2026 AI-NutriCare. All rights reserved.</p>
          <div className="social-links">
            <Link to="/terms" onClick={scrollToTop}>Terms</Link> · <Link to="/privacy" onClick={scrollToTop}>Privacy</Link>
          </div>
        </div>
      </div>
    </footer>
  );
};

export default Footer;
