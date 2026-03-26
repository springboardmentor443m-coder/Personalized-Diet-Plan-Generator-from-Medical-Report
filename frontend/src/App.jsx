import React, { Suspense, lazy } from "react";
import { BrowserRouter as Router, Routes, Route, Navigate } from "react-router-dom";
import { AuthProvider } from "./context/AuthContext";
import Footer from "./components/Footer";
import "./App.css";

// Lazy-loaded components
const Landing = lazy(() => import("./pages/Landing"));
const Login = lazy(() => import("./pages/Login"));
const SignUp = lazy(() => import("./pages/SignUp"));
const Dashboard = lazy(() => import("./pages/Dashboard"));
const SamplePlan = lazy(() => import("./pages/SamplePlan"));

// New Legal & Footer Pages
const Privacy = lazy(() => import("./pages/Privacy"));
const Terms = lazy(() => import("./pages/Terms"));
const HIPAA = lazy(() => import("./pages/HIPAA"));
const GenericPage = lazy(() => import("./pages/GenericPage"));

// A simple fallback UI
const CenteredLoader = () => (
  <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: '100vh', flexDirection: 'column', gap: '20px' }}>
    <div className="floating-loader" style={{ width: '50px', height: '50px', border: '4px solid var(--lavender-light)', borderTop: '4px solid var(--lavender)', borderRadius: '50%', animation: 'spin 1s linear infinite' }} />
    <p style={{ fontFamily: 'Outfit, sans-serif', color: 'var(--lavender)', fontWeight: '600', letterSpacing: '1px' }}>INITIALIZING...</p>
    <style>{`@keyframes spin { 0% { transform: rotate(0deg); } 100% { transform: rotate(360deg); } }`}</style>
  </div>
);

function App() {
  return (
    <Router>
      <AuthProvider>
        <Suspense fallback={<CenteredLoader />}>
          <Routes>
            {/* Core Routes */}
            <Route path="/" element={<Landing />} />
            <Route path="/login" element={<Login />} />
            <Route path="/signup" element={<SignUp />} />
            <Route path="/sample-plan" element={<SamplePlan />} />
            <Route path="/dashboard" element={<Dashboard />} />
            
            {/* Legal & Information Routes */}
            <Route path="/privacy" element={<Privacy />} />
            <Route path="/terms" element={<Terms />} />
            <Route path="/hipaa" element={<HIPAA />} />
            
            {/* Generic Catch-Alls for Footer */}
            <Route path="/about" element={<GenericPage />} />
            <Route path="/contact" element={<GenericPage />} />
            <Route path="/careers" element={<GenericPage />} />
            <Route path="/legitscript" element={<GenericPage />} />
            <Route path="/faq" element={<GenericPage />} />
            <Route path="/feedback" element={<GenericPage />} />
            <Route path="/organizations" element={<GenericPage />} />

            {/* Fallback route */}
            <Route path="*" element={<Navigate to="/" replace />} />
          </Routes>
          <Footer />
        </Suspense>
      </AuthProvider>
    </Router>
  );
}

export default App;